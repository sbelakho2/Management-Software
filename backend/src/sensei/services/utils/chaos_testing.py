"""
Chaos/Failure Mode Testing Service.

Provides comprehensive chaos testing capabilities:
- Job retry verification under failure conditions
- Partial outage simulation (storage, database, network)
- Graceful degradation behavior verification
- Circuit breaker pattern validation
- Recovery time measurement
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


class FailureType(str, Enum):
    """Types of failures to inject."""
    
    STORAGE_DOWN = "storage_down"
    DATABASE_DOWN = "database_down"
    NETWORK_LATENCY = "network_latency"
    NETWORK_PARTITION = "network_partition"
    SERVICE_TIMEOUT = "service_timeout"
    MEMORY_PRESSURE = "memory_pressure"
    CPU_PRESSURE = "cpu_pressure"
    DISK_FULL = "disk_full"
    CONNECTION_EXHAUSTION = "connection_exhaustion"
    DEPENDENCY_FAILURE = "dependency_failure"


class ComponentType(str, Enum):
    """System components that can experience failures."""
    
    DATABASE = "database"
    STORAGE = "storage"
    CACHE = "cache"
    QUEUE = "queue"
    API = "api"
    WORKER = "worker"
    EXTERNAL_SERVICE = "external_service"
    ML_MODEL = "ml_model"


class TestStatus(str, Enum):
    """Status of a chaos test."""

    __test__ = False
    
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


class DegradationLevel(str, Enum):
    """Levels of graceful degradation."""
    
    FULL_FUNCTIONALITY = "full_functionality"
    REDUCED_FEATURES = "reduced_features"
    READ_ONLY = "read_only"
    CACHED_DATA = "cached_data"
    MINIMAL_OPERATION = "minimal_operation"
    COMPLETE_OUTAGE = "complete_outage"


class CircuitState(str, Enum):
    """Circuit breaker states."""
    
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Blocking requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class FailureScenario:
    """Configuration for a failure scenario."""
    
    id: str
    name: str
    description: str
    failure_type: FailureType
    target_component: ComponentType
    duration_seconds: int
    intensity: float  # 0.0 to 1.0 (percentage of requests affected)
    parameters: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class JobRetryTest:
    """Configuration for job retry testing."""
    
    id: str
    job_type: str
    failure_point: str  # Where in the job to inject failure
    max_retries: int
    retry_delay_seconds: int
    expected_recovery: bool  # Whether job should eventually succeed
    failure_count: int = 0
    success_count: int = 0
    final_status: str = "pending"
    attempts: list[dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class DegradationBehavior:
    """Expected behavior during graceful degradation."""
    
    component: ComponentType
    failure_type: FailureType
    expected_level: DegradationLevel
    fallback_behaviors: list[str] = field(default_factory=list)
    user_impact: str = ""
    recovery_behavior: str = ""


@dataclass
class DegradationTest:
    """Test for graceful degradation behavior."""
    
    id: str
    scenario_id: str
    expected_behavior: DegradationBehavior
    actual_level: DegradationLevel | None = None
    fallbacks_triggered: list[str] = field(default_factory=list)
    user_impact_observed: str = ""
    passed: bool = False
    test_duration_ms: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None


@dataclass
class CircuitBreakerState:
    """State of a circuit breaker."""
    
    id: str
    component: str
    state: CircuitState
    failure_count: int
    success_count: int
    last_failure_at: datetime | None
    last_success_at: datetime | None
    opened_at: datetime | None = None
    half_open_attempts: int = 0
    recovery_threshold: int = 3  # Successes needed to close from half-open


@dataclass
class CircuitBreakerTest:
    """Test for circuit breaker behavior."""
    
    id: str
    component: str
    initial_state: CircuitState
    injected_failures: int
    expected_state_after: CircuitState
    actual_state_after: CircuitState | None = None
    passed: bool = False
    state_transitions: list[dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ChaosTestRun:
    """A chaos test run encompassing multiple tests."""
    
    id: str
    name: str
    description: str
    status: TestStatus
    scenarios: list[FailureScenario] = field(default_factory=list)
    job_retry_tests: list[JobRetryTest] = field(default_factory=list)
    degradation_tests: list[DegradationTest] = field(default_factory=list)
    circuit_breaker_tests: list[CircuitBreakerTest] = field(default_factory=list)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class RecoveryMetrics:
    """Metrics for recovery from failure."""
    
    scenario_id: str
    detection_time_ms: int  # Time to detect failure
    isolation_time_ms: int  # Time to isolate failing component
    recovery_time_ms: int  # Time to recover functionality
    data_loss: bool  # Whether data was lost
    data_loss_details: str = ""
    requests_affected: int = 0
    requests_failed: int = 0
    requests_degraded: int = 0


@dataclass
class ChaosTestSummary:
    """Summary of chaos testing results."""
    
    total_runs: int
    completed_runs: int
    total_scenarios: int
    total_job_retry_tests: int
    job_retry_pass_rate: float
    total_degradation_tests: int
    degradation_pass_rate: float
    total_circuit_breaker_tests: int
    circuit_breaker_pass_rate: float
    average_recovery_time_ms: float
    components_tested: list[str]
    failure_types_tested: list[str]
    recommendations: list[str]


class ChaosTestingService:
    """
    Service for chaos/failure mode testing.
    
    Tests system resilience through controlled failure injection:
    - Job retry behavior
    - Partial outages
    - Graceful degradation
    - Circuit breakers
    """
    
    def __init__(self) -> None:
        """Initialize chaos testing service."""
        self._scenarios: dict[str, FailureScenario] = {}
        self._test_runs: dict[str, ChaosTestRun] = {}
        self._job_retry_tests: dict[str, JobRetryTest] = {}
        self._degradation_tests: dict[str, DegradationTest] = {}
        self._circuit_breaker_tests: dict[str, CircuitBreakerTest] = {}
        self._circuit_breakers: dict[str, CircuitBreakerState] = {}
        self._recovery_metrics: dict[str, RecoveryMetrics] = {}
        self._active_failures: dict[str, FailureScenario] = {}
        
        # Define expected degradation behaviors
        self._degradation_behaviors = self._define_degradation_behaviors()
        
        # Track simulation state
        self._simulated_state: dict[str, Any] = {
            "storage_available": True,
            "database_available": True,
            "cache_available": True,
            "queue_available": True,
            "network_latency_ms": 0,
            "memory_usage_percent": 30,
            "cpu_usage_percent": 20,
        }
    
    def _define_degradation_behaviors(self) -> list[DegradationBehavior]:
        """Define expected degradation behaviors for each failure type."""
        return [
            DegradationBehavior(
                component=ComponentType.STORAGE,
                failure_type=FailureType.STORAGE_DOWN,
                expected_level=DegradationLevel.READ_ONLY,
                fallback_behaviors=[
                    "Serve cached documents",
                    "Queue uploads for later",
                    "Display offline indicator",
                ],
                user_impact="Cannot upload new files, can view cached content",
                recovery_behavior="Process queued uploads when storage returns",
            ),
            DegradationBehavior(
                component=ComponentType.DATABASE,
                failure_type=FailureType.DATABASE_DOWN,
                expected_level=DegradationLevel.CACHED_DATA,
                fallback_behaviors=[
                    "Serve cached data",
                    "Queue write operations",
                    "Switch to read-only mode",
                ],
                user_impact="Cannot create/update records, can view cached data",
                recovery_behavior="Replay queued writes when database returns",
            ),
            DegradationBehavior(
                component=ComponentType.CACHE,
                failure_type=FailureType.DEPENDENCY_FAILURE,
                expected_level=DegradationLevel.REDUCED_FEATURES,
                fallback_behaviors=[
                    "Query database directly",
                    "Disable session caching",
                    "Increase response times",
                ],
                user_impact="Slower response times, full functionality available",
                recovery_behavior="Rebuild cache on recovery",
            ),
            DegradationBehavior(
                component=ComponentType.QUEUE,
                failure_type=FailureType.DEPENDENCY_FAILURE,
                expected_level=DegradationLevel.REDUCED_FEATURES,
                fallback_behaviors=[
                    "Process jobs synchronously",
                    "Queue to local filesystem",
                    "Delay non-critical operations",
                ],
                user_impact="Slower background operations, main features work",
                recovery_behavior="Process local queue when service returns",
            ),
            DegradationBehavior(
                component=ComponentType.EXTERNAL_SERVICE,
                failure_type=FailureType.SERVICE_TIMEOUT,
                expected_level=DegradationLevel.REDUCED_FEATURES,
                fallback_behaviors=[
                    "Use cached external data",
                    "Skip optional enrichment",
                    "Show partial information",
                ],
                user_impact="Missing external data, core features work",
                recovery_behavior="Refresh external data when service returns",
            ),
            DegradationBehavior(
                component=ComponentType.ML_MODEL,
                failure_type=FailureType.MEMORY_PRESSURE,
                expected_level=DegradationLevel.REDUCED_FEATURES,
                fallback_behaviors=[
                    "Fall back to simpler model",
                    "Use rule-based processing",
                    "Disable AI suggestions",
                ],
                user_impact="AI features unavailable, manual workflow works",
                recovery_behavior="Reload model when memory available",
            ),
        ]
    
    # ===== Scenario Management =====
    
    def create_scenario(
        self,
        name: str,
        description: str,
        failure_type: FailureType,
        target_component: ComponentType,
        duration_seconds: int = 60,
        intensity: float = 1.0,
        parameters: dict[str, Any] | None = None,
    ) -> FailureScenario:
        """Create a new failure scenario."""
        if intensity < 0.0 or intensity > 1.0:
            raise ValueError("Intensity must be between 0.0 and 1.0")
        if duration_seconds < 1:
            raise ValueError("Duration must be at least 1 second")
        
        scenario = FailureScenario(
            id=str(uuid4()),
            name=name,
            description=description,
            failure_type=failure_type,
            target_component=target_component,
            duration_seconds=duration_seconds,
            intensity=intensity,
            parameters=parameters or {},
        )
        self._scenarios[scenario.id] = scenario
        return scenario
    
    def get_scenario(self, scenario_id: str) -> FailureScenario | None:
        """Get a scenario by ID."""
        return self._scenarios.get(scenario_id)
    
    def list_scenarios(self) -> list[FailureScenario]:
        """List all failure scenarios."""
        return list(self._scenarios.values())
    
    def delete_scenario(self, scenario_id: str) -> bool:
        """Delete a scenario."""
        if scenario_id in self._active_failures:
            raise ValueError("Cannot delete active failure scenario")
        if scenario_id in self._scenarios:
            del self._scenarios[scenario_id]
            return True
        return False
    
    # ===== Failure Injection =====
    
    def inject_failure(self, scenario_id: str) -> dict[str, Any]:
        """Inject a failure based on scenario configuration."""
        scenario = self._scenarios.get(scenario_id)
        if not scenario:
            raise ValueError(f"Scenario {scenario_id} not found")
        
        # Track active failure
        self._active_failures[scenario_id] = scenario
        
        # Update simulated state based on failure type
        self._apply_failure(scenario)
        
        return {
            "scenario_id": scenario_id,
            "failure_type": scenario.failure_type.value,
            "target_component": scenario.target_component.value,
            "injected_at": datetime.now(timezone.utc).isoformat(),
            "duration_seconds": scenario.duration_seconds,
            "intensity": scenario.intensity,
            "state": self._simulated_state.copy(),
        }
    
    def _apply_failure(self, scenario: FailureScenario) -> None:
        """Apply failure effects to simulated state."""
        if scenario.failure_type == FailureType.STORAGE_DOWN:
            self._simulated_state["storage_available"] = False
        elif scenario.failure_type == FailureType.DATABASE_DOWN:
            self._simulated_state["database_available"] = False
        elif scenario.failure_type == FailureType.NETWORK_LATENCY:
            latency = scenario.parameters.get("latency_ms", 5000)
            self._simulated_state["network_latency_ms"] = latency
        elif scenario.failure_type == FailureType.MEMORY_PRESSURE:
            usage = scenario.parameters.get("usage_percent", 95)
            self._simulated_state["memory_usage_percent"] = usage
        elif scenario.failure_type == FailureType.CPU_PRESSURE:
            usage = scenario.parameters.get("usage_percent", 95)
            self._simulated_state["cpu_usage_percent"] = usage
        elif scenario.failure_type == FailureType.DEPENDENCY_FAILURE:
            component = scenario.target_component.value
            if component == "cache":
                self._simulated_state["cache_available"] = False
            elif component == "queue":
                self._simulated_state["queue_available"] = False
    
    def remove_failure(self, scenario_id: str) -> dict[str, Any]:
        """Remove an injected failure."""
        scenario = self._active_failures.pop(scenario_id, None)
        if not scenario:
            raise ValueError(f"No active failure for scenario {scenario_id}")
        
        # Restore simulated state
        self._restore_from_failure(scenario)
        
        return {
            "scenario_id": scenario_id,
            "removed_at": datetime.now(timezone.utc).isoformat(),
            "state": self._simulated_state.copy(),
        }
    
    def _restore_from_failure(self, scenario: FailureScenario) -> None:
        """Restore state after failure removal."""
        if scenario.failure_type == FailureType.STORAGE_DOWN:
            self._simulated_state["storage_available"] = True
        elif scenario.failure_type == FailureType.DATABASE_DOWN:
            self._simulated_state["database_available"] = True
        elif scenario.failure_type == FailureType.NETWORK_LATENCY:
            self._simulated_state["network_latency_ms"] = 0
        elif scenario.failure_type == FailureType.MEMORY_PRESSURE:
            self._simulated_state["memory_usage_percent"] = 30
        elif scenario.failure_type == FailureType.CPU_PRESSURE:
            self._simulated_state["cpu_usage_percent"] = 20
        elif scenario.failure_type == FailureType.DEPENDENCY_FAILURE:
            component = scenario.target_component.value
            if component == "cache":
                self._simulated_state["cache_available"] = True
            elif component == "queue":
                self._simulated_state["queue_available"] = True
    
    def get_active_failures(self) -> list[dict[str, Any]]:
        """Get all active failure injections."""
        return [
            {
                "scenario_id": s.id,
                "name": s.name,
                "failure_type": s.failure_type.value,
                "target_component": s.target_component.value,
            }
            for s in self._active_failures.values()
        ]
    
    def get_system_state(self) -> dict[str, Any]:
        """Get current simulated system state."""
        return self._simulated_state.copy()
    
    # ===== Job Retry Testing =====
    
    def create_job_retry_test(
        self,
        job_type: str,
        failure_point: str,
        max_retries: int = 3,
        retry_delay_seconds: int = 5,
        expected_recovery: bool = True,
    ) -> JobRetryTest:
        """Create a job retry test configuration."""
        test = JobRetryTest(
            id=str(uuid4()),
            job_type=job_type,
            failure_point=failure_point,
            max_retries=max_retries,
            retry_delay_seconds=retry_delay_seconds,
            expected_recovery=expected_recovery,
        )
        self._job_retry_tests[test.id] = test
        return test
    
    def simulate_job_execution(
        self,
        test_id: str,
        fail_until_attempt: int = 2,
    ) -> JobRetryTest:
        """
        Simulate job execution with failures.
        
        Args:
            test_id: The job retry test ID
            fail_until_attempt: Fail until this attempt number (then succeed)
        """
        test = self._job_retry_tests.get(test_id)
        if not test:
            raise ValueError(f"Job retry test {test_id} not found")
        
        test.attempts = []
        test.failure_count = 0
        test.success_count = 0
        
        for attempt in range(1, test.max_retries + 2):  # +1 for initial, +1 for last retry
            attempt_result = {
                "attempt": attempt,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "failure_point": test.failure_point,
            }
            
            if attempt < fail_until_attempt:
                # Simulate failure
                attempt_result["status"] = "failed"
                attempt_result["error"] = f"Simulated failure at {test.failure_point}"
                test.failure_count += 1
            else:
                # Simulate success
                attempt_result["status"] = "success"
                test.success_count += 1
                test.attempts.append(attempt_result)
                break
            
            test.attempts.append(attempt_result)
            
            if attempt > test.max_retries:
                # Max retries exceeded
                break
        
        # Determine final status
        if test.success_count > 0:
            test.final_status = "recovered"
        elif test.failure_count > test.max_retries:
            test.final_status = "exhausted_retries"
        else:
            test.final_status = "in_progress"
        
        return test
    
    def get_job_retry_test(self, test_id: str) -> JobRetryTest | None:
        """Get a job retry test by ID."""
        return self._job_retry_tests.get(test_id)
    
    def list_job_retry_tests(self) -> list[JobRetryTest]:
        """List all job retry tests."""
        return list(self._job_retry_tests.values())
    
    def validate_job_retry_behavior(self, test_id: str) -> dict[str, Any]:
        """Validate that job retry behavior matches expectations."""
        test = self._job_retry_tests.get(test_id)
        if not test:
            raise ValueError(f"Job retry test {test_id} not found")
        
        checks: list[dict[str, Any]] = []
        validation: dict[str, Any] = {
            "test_id": test_id,
            "job_type": test.job_type,
            "passed": False,
            "checks": checks,
        }
        
        # Check 1: Retries occurred
        retry_check = {
            "name": "retries_executed",
            "expected": test.max_retries if test.failure_count > 0 else 0,
            "actual": len(test.attempts) - 1 if test.success_count > 0 else len(test.attempts),
            "passed": True,
        }
        if test.failure_count > 0 and len(test.attempts) < 2:
            retry_check["passed"] = False
        checks.append(retry_check)
        
        # Check 2: Recovery matches expectation
        recovery_check = {
            "name": "recovery_behavior",
            "expected_recovery": test.expected_recovery,
            "actual_recovery": test.final_status == "recovered",
            "passed": (test.final_status == "recovered") == test.expected_recovery,
        }
        checks.append(recovery_check)
        
        # Check 3: Failure point captured
        failure_point_check = {
            "name": "failure_point_logged",
            "expected": test.failure_point,
            "passed": all(
                a.get("failure_point") == test.failure_point
                for a in test.attempts
            ),
        }
        checks.append(failure_point_check)
        
        # Overall pass/fail
        validation["passed"] = all(c["passed"] for c in checks)
        
        return validation
    
    # ===== Graceful Degradation Testing =====
    
    def create_degradation_test(
        self,
        scenario_id: str,
    ) -> DegradationTest:
        """Create a degradation test based on a failure scenario."""
        scenario = self._scenarios.get(scenario_id)
        if not scenario:
            raise ValueError(f"Scenario {scenario_id} not found")
        
        # Find matching expected behavior
        expected = None
        for behavior in self._degradation_behaviors:
            if (
                behavior.component == scenario.target_component
                and behavior.failure_type == scenario.failure_type
            ):
                expected = behavior
                break
        
        if not expected:
            # Create generic expected behavior
            expected = DegradationBehavior(
                component=scenario.target_component,
                failure_type=scenario.failure_type,
                expected_level=DegradationLevel.REDUCED_FEATURES,
                fallback_behaviors=["Log warning", "Continue with reduced functionality"],
                user_impact="Some features unavailable",
                recovery_behavior="Resume normal operation when component returns",
            )
        
        test = DegradationTest(
            id=str(uuid4()),
            scenario_id=scenario_id,
            expected_behavior=expected,
        )
        self._degradation_tests[test.id] = test
        return test
    
    def execute_degradation_test(self, test_id: str) -> DegradationTest:
        """Execute a graceful degradation test."""
        test = self._degradation_tests.get(test_id)
        if not test:
            raise ValueError(f"Degradation test {test_id} not found")
        
        test.started_at = datetime.now(timezone.utc)
        
        # Inject the failure
        scenario = self._scenarios.get(test.scenario_id)
        if not scenario:
            raise ValueError(f"Scenario {test.scenario_id} not found")
        
        self.inject_failure(test.scenario_id)
        
        # Simulate checking system behavior
        # In a real implementation, this would make actual requests
        test.actual_level = self._determine_degradation_level(scenario)
        test.fallbacks_triggered = self._determine_fallbacks_triggered(scenario)
        test.user_impact_observed = test.expected_behavior.user_impact
        
        # Clean up
        self.remove_failure(test.scenario_id)
        
        test.completed_at = datetime.now(timezone.utc)
        test.test_duration_ms = int(
            (test.completed_at - test.started_at).total_seconds() * 1000
        )
        
        # Validate results
        test.passed = (
            test.actual_level == test.expected_behavior.expected_level
            and len(test.fallbacks_triggered) > 0
        )
        
        return test
    
    def _determine_degradation_level(self, scenario: FailureScenario) -> DegradationLevel:
        """Determine the degradation level based on scenario."""
        if scenario.failure_type == FailureType.STORAGE_DOWN:
            return DegradationLevel.READ_ONLY
        elif scenario.failure_type == FailureType.DATABASE_DOWN:
            return DegradationLevel.CACHED_DATA
        elif scenario.failure_type == FailureType.NETWORK_PARTITION:
            return DegradationLevel.COMPLETE_OUTAGE
        elif scenario.failure_type in (
            FailureType.NETWORK_LATENCY,
            FailureType.SERVICE_TIMEOUT,
        ):
            return DegradationLevel.REDUCED_FEATURES
        elif scenario.failure_type in (
            FailureType.MEMORY_PRESSURE,
            FailureType.CPU_PRESSURE,
        ):
            return DegradationLevel.REDUCED_FEATURES
        else:
            return DegradationLevel.REDUCED_FEATURES
    
    def _determine_fallbacks_triggered(self, scenario: FailureScenario) -> list[str]:
        """Determine which fallbacks were triggered."""
        fallbacks = []
        
        if scenario.failure_type == FailureType.STORAGE_DOWN:
            fallbacks.extend([
                "Serve cached documents",
                "Queue uploads for later",
            ])
        elif scenario.failure_type == FailureType.DATABASE_DOWN:
            fallbacks.extend([
                "Serve cached data",
                "Queue write operations",
            ])
        elif scenario.failure_type == FailureType.NETWORK_LATENCY:
            fallbacks.append("Increase timeout thresholds")
        elif scenario.failure_type == FailureType.MEMORY_PRESSURE:
            fallbacks.extend([
                "Reduce batch sizes",
                "Disable non-essential features",
            ])
        else:
            fallbacks.append("Log warning and continue")
        
        return fallbacks
    
    def get_degradation_test(self, test_id: str) -> DegradationTest | None:
        """Get a degradation test by ID."""
        return self._degradation_tests.get(test_id)
    
    def list_degradation_tests(self) -> list[DegradationTest]:
        """List all degradation tests."""
        return list(self._degradation_tests.values())
    
    # ===== Circuit Breaker Testing =====
    
    def register_circuit_breaker(
        self,
        component: str,
        recovery_threshold: int = 3,
    ) -> CircuitBreakerState:
        """Register a circuit breaker for monitoring."""
        state = CircuitBreakerState(
            id=str(uuid4()),
            component=component,
            state=CircuitState.CLOSED,
            failure_count=0,
            success_count=0,
            last_failure_at=None,
            last_success_at=None,
            recovery_threshold=recovery_threshold,
        )
        self._circuit_breakers[state.id] = state
        return state
    
    def get_circuit_breaker(self, breaker_id: str) -> CircuitBreakerState | None:
        """Get a circuit breaker by ID."""
        return self._circuit_breakers.get(breaker_id)
    
    def list_circuit_breakers(self) -> list[CircuitBreakerState]:
        """List all circuit breakers."""
        return list(self._circuit_breakers.values())
    
    def record_circuit_breaker_failure(self, breaker_id: str) -> CircuitBreakerState:
        """Record a failure for a circuit breaker."""
        breaker = self._circuit_breakers.get(breaker_id)
        if not breaker:
            raise ValueError(f"Circuit breaker {breaker_id} not found")
        
        breaker.failure_count += 1
        breaker.last_failure_at = datetime.now(timezone.utc)
        
        # Check if should open
        if breaker.state == CircuitState.CLOSED and breaker.failure_count >= 5:
            breaker.state = CircuitState.OPEN
            breaker.opened_at = datetime.now(timezone.utc)
        elif breaker.state == CircuitState.HALF_OPEN:
            # Any failure in half-open returns to open
            breaker.state = CircuitState.OPEN
            breaker.opened_at = datetime.now(timezone.utc)
            breaker.half_open_attempts = 0
        
        return breaker
    
    def record_circuit_breaker_success(self, breaker_id: str) -> CircuitBreakerState:
        """Record a success for a circuit breaker."""
        breaker = self._circuit_breakers.get(breaker_id)
        if not breaker:
            raise ValueError(f"Circuit breaker {breaker_id} not found")
        
        breaker.success_count += 1
        breaker.last_success_at = datetime.now(timezone.utc)
        
        if breaker.state == CircuitState.HALF_OPEN:
            breaker.half_open_attempts += 1
            if breaker.half_open_attempts >= breaker.recovery_threshold:
                # Enough successes to close
                breaker.state = CircuitState.CLOSED
                breaker.failure_count = 0
                breaker.half_open_attempts = 0
        elif breaker.state == CircuitState.CLOSED:
            # Reset failure count on success
            breaker.failure_count = max(0, breaker.failure_count - 1)
        
        return breaker
    
    def attempt_circuit_breaker_reset(self, breaker_id: str) -> CircuitBreakerState:
        """Attempt to reset circuit breaker to half-open."""
        breaker = self._circuit_breakers.get(breaker_id)
        if not breaker:
            raise ValueError(f"Circuit breaker {breaker_id} not found")
        
        if breaker.state == CircuitState.OPEN:
            breaker.state = CircuitState.HALF_OPEN
            breaker.half_open_attempts = 0
        
        return breaker
    
    def create_circuit_breaker_test(
        self,
        breaker_id: str,
        injected_failures: int,
        expected_state_after: CircuitState,
    ) -> CircuitBreakerTest:
        """Create a circuit breaker test."""
        breaker = self._circuit_breakers.get(breaker_id)
        if not breaker:
            raise ValueError(f"Circuit breaker {breaker_id} not found")
        
        test = CircuitBreakerTest(
            id=str(uuid4()),
            component=breaker.component,
            initial_state=breaker.state,
            injected_failures=injected_failures,
            expected_state_after=expected_state_after,
        )
        self._circuit_breaker_tests[test.id] = test
        return test
    
    def execute_circuit_breaker_test(
        self,
        test_id: str,
        breaker_id: str,
    ) -> CircuitBreakerTest:
        """Execute a circuit breaker test."""
        test = self._circuit_breaker_tests.get(test_id)
        if not test:
            raise ValueError(f"Circuit breaker test {test_id} not found")
        
        breaker = self._circuit_breakers.get(breaker_id)
        if not breaker:
            raise ValueError(f"Circuit breaker {breaker_id} not found")
        
        test.initial_state = breaker.state
        test.state_transitions = []
        
        # Inject failures
        for i in range(test.injected_failures):
            old_state = breaker.state
            self.record_circuit_breaker_failure(breaker_id)
            if breaker.state != old_state:
                test.state_transitions.append({
                    "failure_number": i + 1,
                    "from_state": old_state.value,
                    "to_state": breaker.state.value,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
        
        test.actual_state_after = breaker.state
        test.passed = test.actual_state_after == test.expected_state_after
        
        return test
    
    def get_circuit_breaker_test(self, test_id: str) -> CircuitBreakerTest | None:
        """Get a circuit breaker test by ID."""
        return self._circuit_breaker_tests.get(test_id)
    
    def list_circuit_breaker_tests(self) -> list[CircuitBreakerTest]:
        """List all circuit breaker tests."""
        return list(self._circuit_breaker_tests.values())
    
    # ===== Test Run Management =====
    
    def create_test_run(
        self,
        name: str,
        description: str,
        scenario_ids: list[str] | None = None,
    ) -> ChaosTestRun:
        """Create a new chaos test run."""
        run = ChaosTestRun(
            id=str(uuid4()),
            name=name,
            description=description,
            status=TestStatus.PENDING,
        )
        
        if scenario_ids:
            for sid in scenario_ids:
                scenario = self._scenarios.get(sid)
                if scenario:
                    run.scenarios.append(scenario)
        
        self._test_runs[run.id] = run
        return run
    
    def start_test_run(self, run_id: str) -> ChaosTestRun:
        """Start a chaos test run."""
        run = self._test_runs.get(run_id)
        if not run:
            raise ValueError(f"Test run {run_id} not found")
        
        run.status = TestStatus.RUNNING
        run.started_at = datetime.now(timezone.utc)
        
        # Execute tests for each scenario
        for scenario in run.scenarios:
            # Create and execute degradation test
            deg_test = self.create_degradation_test(scenario.id)
            self.execute_degradation_test(deg_test.id)
            run.degradation_tests.append(deg_test)
            run.total_tests += 1
            if deg_test.passed:
                run.passed_tests += 1
            else:
                run.failed_tests += 1
        
        # Execute job retry tests
        for test in self._job_retry_tests.values():
            if test.final_status == "pending":
                self.simulate_job_execution(test.id, fail_until_attempt=2)
                validation = self.validate_job_retry_behavior(test.id)
                run.job_retry_tests.append(test)
                run.total_tests += 1
                if validation["passed"]:
                    run.passed_tests += 1
                else:
                    run.failed_tests += 1
        
        # Execute circuit breaker tests
        for cb_test in self._circuit_breaker_tests.values():
            if cb_test.actual_state_after is None:
                # Find matching breaker
                for breaker in self._circuit_breakers.values():
                    if breaker.component == cb_test.component:
                        self.execute_circuit_breaker_test(cb_test.id, breaker.id)
                        break
                run.circuit_breaker_tests.append(cb_test)
                run.total_tests += 1
                if cb_test.passed:
                    run.passed_tests += 1
                else:
                    run.failed_tests += 1
        
        run.status = TestStatus.COMPLETED
        run.completed_at = datetime.now(timezone.utc)
        
        return run
    
    def abort_test_run(self, run_id: str) -> ChaosTestRun:
        """Abort a running chaos test run."""
        run = self._test_runs.get(run_id)
        if not run:
            raise ValueError(f"Test run {run_id} not found")
        
        if run.status != TestStatus.RUNNING:
            raise ValueError("Can only abort running tests")
        
        # Clean up any active failures
        for scenario_id in list(self._active_failures.keys()):
            self.remove_failure(scenario_id)
        
        run.status = TestStatus.ABORTED
        run.completed_at = datetime.now(timezone.utc)
        
        return run
    
    def get_test_run(self, run_id: str) -> ChaosTestRun | None:
        """Get a test run by ID."""
        return self._test_runs.get(run_id)
    
    def list_test_runs(self) -> list[ChaosTestRun]:
        """List all test runs."""
        return list(self._test_runs.values())
    
    # ===== Recovery Metrics =====
    
    def record_recovery_metrics(
        self,
        scenario_id: str,
        detection_time_ms: int,
        isolation_time_ms: int,
        recovery_time_ms: int,
        data_loss: bool = False,
        data_loss_details: str = "",
        requests_affected: int = 0,
        requests_failed: int = 0,
        requests_degraded: int = 0,
    ) -> RecoveryMetrics:
        """Record recovery metrics for a failure scenario."""
        metrics = RecoveryMetrics(
            scenario_id=scenario_id,
            detection_time_ms=detection_time_ms,
            isolation_time_ms=isolation_time_ms,
            recovery_time_ms=recovery_time_ms,
            data_loss=data_loss,
            data_loss_details=data_loss_details,
            requests_affected=requests_affected,
            requests_failed=requests_failed,
            requests_degraded=requests_degraded,
        )
        self._recovery_metrics[scenario_id] = metrics
        return metrics
    
    def get_recovery_metrics(self, scenario_id: str) -> RecoveryMetrics | None:
        """Get recovery metrics for a scenario."""
        return self._recovery_metrics.get(scenario_id)
    
    def list_recovery_metrics(self) -> list[RecoveryMetrics]:
        """List all recovery metrics."""
        return list(self._recovery_metrics.values())
    
    # ===== Summary and Reporting =====
    
    def get_summary(self) -> ChaosTestSummary:
        """Get a summary of all chaos testing results."""
        runs = list(self._test_runs.values())
        completed_runs = [r for r in runs if r.status == TestStatus.COMPLETED]
        
        # Calculate pass rates
        job_tests = list(self._job_retry_tests.values())
        job_passed = sum(
            1 for t in job_tests
            if t.final_status == "recovered" and t.expected_recovery
            or t.final_status == "exhausted_retries" and not t.expected_recovery
        )
        job_pass_rate = job_passed / len(job_tests) if job_tests else 0.0
        
        deg_tests = list(self._degradation_tests.values())
        deg_passed = sum(1 for t in deg_tests if t.passed)
        deg_pass_rate = deg_passed / len(deg_tests) if deg_tests else 0.0
        
        cb_tests = list(self._circuit_breaker_tests.values())
        cb_passed = sum(1 for t in cb_tests if t.passed)
        cb_pass_rate = cb_passed / len(cb_tests) if cb_tests else 0.0
        
        # Calculate average recovery time
        metrics = list(self._recovery_metrics.values())
        avg_recovery = (
            sum(m.recovery_time_ms for m in metrics) / len(metrics)
            if metrics else 0.0
        )
        
        # Collect tested components and failure types
        components = set()
        failure_types = set()
        for scenario in self._scenarios.values():
            components.add(scenario.target_component.value)
            failure_types.add(scenario.failure_type.value)
        
        # Generate recommendations
        recommendations = []
        if job_pass_rate < 1.0:
            recommendations.append("Review job retry configuration for failing jobs")
        if deg_pass_rate < 1.0:
            recommendations.append(
                "Implement additional fallback behaviors for graceful degradation"
            )
        if cb_pass_rate < 1.0:
            recommendations.append("Tune circuit breaker thresholds")
        if avg_recovery > 30000:
            recommendations.append(
                "Reduce recovery time - current average exceeds 30 seconds"
            )
        if len(components) < len(ComponentType):
            missing = set(c.value for c in ComponentType) - components
            recommendations.append(f"Expand testing to cover: {', '.join(missing)}")
        
        return ChaosTestSummary(
            total_runs=len(runs),
            completed_runs=len(completed_runs),
            total_scenarios=len(self._scenarios),
            total_job_retry_tests=len(job_tests),
            job_retry_pass_rate=job_pass_rate,
            total_degradation_tests=len(deg_tests),
            degradation_pass_rate=deg_pass_rate,
            total_circuit_breaker_tests=len(cb_tests),
            circuit_breaker_pass_rate=cb_pass_rate,
            average_recovery_time_ms=avg_recovery,
            components_tested=sorted(components),
            failure_types_tested=sorted(failure_types),
            recommendations=recommendations,
        )
    
    def clear_all_data(self) -> None:
        """Clear all test data."""
        self._scenarios.clear()
        self._test_runs.clear()
        self._job_retry_tests.clear()
        self._degradation_tests.clear()
        self._circuit_breaker_tests.clear()
        self._circuit_breakers.clear()
        self._recovery_metrics.clear()
        self._active_failures.clear()
        self._simulated_state = {
            "storage_available": True,
            "database_available": True,
            "cache_available": True,
            "queue_available": True,
            "network_latency_ms": 0,
            "memory_usage_percent": 30,
            "cpu_usage_percent": 20,
        }


# Singleton instance
_chaos_testing_service: ChaosTestingService | None = None


def get_chaos_testing_service() -> ChaosTestingService:
    """Get the singleton chaos testing service instance."""
    global _chaos_testing_service
    if _chaos_testing_service is None:
        _chaos_testing_service = ChaosTestingService()
    return _chaos_testing_service


def reset_chaos_testing_service() -> None:
    """Reset the chaos testing service (for testing)."""
    global _chaos_testing_service
    if _chaos_testing_service is not None:
        _chaos_testing_service.clear_all_data()
    _chaos_testing_service = None
