"""
Chaos/Failure Mode Testing API Endpoints.

Provides REST API for chaos testing:
- Failure scenario management
- Failure injection and removal
- Job retry testing
- Graceful degradation testing
- Circuit breaker testing
- Test run management
- Summary and reporting
"""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from sensei.api.deps import CurrentSuperuser
from sensei.services.utils.chaos_testing import (
    CircuitState,
    ComponentType,
    DegradationLevel,
    FailureType,
    TestStatus,
    get_chaos_testing_service,
)


router = APIRouter()


# ===== Request/Response Models =====


class CreateScenarioRequest(BaseModel):
    """Request to create a failure scenario."""
    
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1)
    failure_type: str = Field(...)
    target_component: str = Field(...)
    duration_seconds: int = Field(default=60, ge=1)
    intensity: float = Field(default=1.0, ge=0.0, le=1.0)
    parameters: dict[str, Any] = Field(default_factory=dict)


class ScenarioResponse(BaseModel):
    """Response for a failure scenario."""
    
    id: str
    name: str
    description: str
    failure_type: str
    target_component: str
    duration_seconds: int
    intensity: float
    parameters: dict[str, Any]
    created_at: str


class FailureInjectionResponse(BaseModel):
    """Response for failure injection."""
    
    scenario_id: str
    failure_type: str
    target_component: str
    injected_at: str
    duration_seconds: int
    intensity: float
    state: dict[str, Any]


class SystemStateResponse(BaseModel):
    """Response for system state."""
    
    storage_available: bool
    database_available: bool
    cache_available: bool
    queue_available: bool
    network_latency_ms: int
    memory_usage_percent: int
    cpu_usage_percent: int


class CreateJobRetryTestRequest(BaseModel):
    """Request to create a job retry test."""
    
    job_type: str = Field(..., min_length=1)
    failure_point: str = Field(..., min_length=1)
    max_retries: int = Field(default=3, ge=1)
    retry_delay_seconds: int = Field(default=5, ge=1)
    expected_recovery: bool = Field(default=True)


class JobRetryTestResponse(BaseModel):
    """Response for a job retry test."""
    
    id: str
    job_type: str
    failure_point: str
    max_retries: int
    retry_delay_seconds: int
    expected_recovery: bool
    failure_count: int
    success_count: int
    final_status: str
    attempts: list[dict[str, Any]]


class SimulateJobRequest(BaseModel):
    """Request to simulate job execution."""
    
    fail_until_attempt: int = Field(default=2, ge=1)


class JobRetryValidationResponse(BaseModel):
    """Response for job retry validation."""
    
    test_id: str
    job_type: str
    passed: bool
    checks: list[dict[str, Any]]


class DegradationTestResponse(BaseModel):
    """Response for a degradation test."""
    
    id: str
    scenario_id: str
    expected_level: str
    actual_level: str | None
    fallbacks_triggered: list[str]
    passed: bool
    test_duration_ms: int


class RegisterCircuitBreakerRequest(BaseModel):
    """Request to register a circuit breaker."""
    
    component: str = Field(..., min_length=1)
    recovery_threshold: int = Field(default=3, ge=1)


class CircuitBreakerResponse(BaseModel):
    """Response for a circuit breaker."""
    
    id: str
    component: str
    state: str
    failure_count: int
    success_count: int
    half_open_attempts: int
    recovery_threshold: int


class CreateCircuitBreakerTestRequest(BaseModel):
    """Request to create a circuit breaker test."""
    
    breaker_id: str = Field(...)
    injected_failures: int = Field(..., ge=1)
    expected_state_after: str = Field(...)


class CircuitBreakerTestResponse(BaseModel):
    """Response for a circuit breaker test."""
    
    id: str
    component: str
    initial_state: str
    injected_failures: int
    expected_state_after: str
    actual_state_after: str | None
    passed: bool
    state_transitions: list[dict[str, Any]]


class CreateTestRunRequest(BaseModel):
    """Request to create a test run."""
    
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(...)
    scenario_ids: list[str] = Field(default_factory=list)


class TestRunResponse(BaseModel):
    """Response for a test run."""
    
    id: str
    name: str
    description: str
    status: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    started_at: str | None
    completed_at: str | None


class RecordRecoveryMetricsRequest(BaseModel):
    """Request to record recovery metrics."""
    
    scenario_id: str = Field(...)
    detection_time_ms: int = Field(..., ge=0)
    isolation_time_ms: int = Field(..., ge=0)
    recovery_time_ms: int = Field(..., ge=0)
    data_loss: bool = Field(default=False)
    data_loss_details: str = Field(default="")
    requests_affected: int = Field(default=0, ge=0)
    requests_failed: int = Field(default=0, ge=0)
    requests_degraded: int = Field(default=0, ge=0)


class RecoveryMetricsResponse(BaseModel):
    """Response for recovery metrics."""
    
    scenario_id: str
    detection_time_ms: int
    isolation_time_ms: int
    recovery_time_ms: int
    data_loss: bool
    data_loss_details: str
    requests_affected: int
    requests_failed: int
    requests_degraded: int


class ChaosSummaryResponse(BaseModel):
    """Response for chaos testing summary."""
    
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


# ===== Validation Helpers =====


def validate_failure_type(value: str) -> FailureType:
    """Validate and convert failure type string."""
    try:
        return FailureType(value)
    except ValueError:
        valid = [ft.value for ft in FailureType]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid failure_type. Must be one of: {valid}",
        )


def validate_component_type(value: str) -> ComponentType:
    """Validate and convert component type string."""
    try:
        return ComponentType(value)
    except ValueError:
        valid = [ct.value for ct in ComponentType]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid target_component. Must be one of: {valid}",
        )


def validate_circuit_state(value: str) -> CircuitState:
    """Validate and convert circuit state string."""
    try:
        return CircuitState(value)
    except ValueError:
        valid = [cs.value for cs in CircuitState]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid circuit state. Must be one of: {valid}",
        )


# ===== Scenario Endpoints =====


@router.post(
    "/scenarios",
    response_model=ScenarioResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_scenario(request: CreateScenarioRequest, current_user: CurrentSuperuser):
    """Create a new failure scenario."""
    service = get_chaos_testing_service()
    
    failure_type = validate_failure_type(request.failure_type)
    component = validate_component_type(request.target_component)
    
    try:
        scenario = service.create_scenario(
            name=request.name,
            description=request.description,
            failure_type=failure_type,
            target_component=component,
            duration_seconds=request.duration_seconds,
            intensity=request.intensity,
            parameters=request.parameters,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    return ScenarioResponse(
        id=scenario.id,
        name=scenario.name,
        description=scenario.description,
        failure_type=scenario.failure_type.value,
        target_component=scenario.target_component.value,
        duration_seconds=scenario.duration_seconds,
        intensity=scenario.intensity,
        parameters=scenario.parameters,
        created_at=scenario.created_at.isoformat(),
    )


@router.get("/scenarios", response_model=list[ScenarioResponse])
def list_scenarios(current_user: CurrentSuperuser):
    """List all failure scenarios."""
    service = get_chaos_testing_service()
    scenarios = service.list_scenarios()
    
    return [
        ScenarioResponse(
            id=s.id,
            name=s.name,
            description=s.description,
            failure_type=s.failure_type.value,
            target_component=s.target_component.value,
            duration_seconds=s.duration_seconds,
            intensity=s.intensity,
            parameters=s.parameters,
            created_at=s.created_at.isoformat(),
        )
        for s in scenarios
    ]


@router.get("/scenarios/{scenario_id}", response_model=ScenarioResponse)
def get_scenario(scenario_id: str, current_user: CurrentSuperuser):
    """Get a failure scenario by ID."""
    service = get_chaos_testing_service()
    scenario = service.get_scenario(scenario_id)
    
    if not scenario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario not found",
        )
    
    return ScenarioResponse(
        id=scenario.id,
        name=scenario.name,
        description=scenario.description,
        failure_type=scenario.failure_type.value,
        target_component=scenario.target_component.value,
        duration_seconds=scenario.duration_seconds,
        intensity=scenario.intensity,
        parameters=scenario.parameters,
        created_at=scenario.created_at.isoformat(),
    )


@router.delete("/scenarios/{scenario_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_scenario(scenario_id: str, current_user: CurrentSuperuser):
    """Delete a failure scenario."""
    service = get_chaos_testing_service()
    
    try:
        deleted = service.delete_scenario(scenario_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scenario not found",
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# ===== Failure Injection Endpoints =====


@router.post(
    "/failures/{scenario_id}/inject",
    response_model=FailureInjectionResponse,
)
def inject_failure(scenario_id: str, current_user: CurrentSuperuser):
    """Inject a failure based on a scenario."""
    service = get_chaos_testing_service()
    
    try:
        result = service.inject_failure(scenario_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    
    return FailureInjectionResponse(
        scenario_id=result["scenario_id"],
        failure_type=result["failure_type"],
        target_component=result["target_component"],
        injected_at=result["injected_at"],
        duration_seconds=result["duration_seconds"],
        intensity=result["intensity"],
        state=result["state"],
    )


@router.post("/failures/{scenario_id}/remove")
def remove_failure(scenario_id: str, current_user: CurrentSuperuser):
    """Remove an injected failure."""
    service = get_chaos_testing_service()
    
    try:
        result = service.remove_failure(scenario_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    
    return {
        "scenario_id": result["scenario_id"],
        "removed_at": result["removed_at"],
        "state": result["state"],
    }


@router.get("/failures/active")
def get_active_failures(current_user: CurrentSuperuser):
    """Get all active failure injections."""
    service = get_chaos_testing_service()
    return service.get_active_failures()


@router.get("/state", response_model=SystemStateResponse)
def get_system_state(current_user: CurrentSuperuser):
    """Get current simulated system state."""
    service = get_chaos_testing_service()
    state = service.get_system_state()
    return SystemStateResponse(**state)


# ===== Job Retry Test Endpoints =====


@router.post(
    "/job-retry-tests",
    response_model=JobRetryTestResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_job_retry_test(request: CreateJobRetryTestRequest, current_user: CurrentSuperuser):
    """Create a job retry test."""
    service = get_chaos_testing_service()
    
    test = service.create_job_retry_test(
        job_type=request.job_type,
        failure_point=request.failure_point,
        max_retries=request.max_retries,
        retry_delay_seconds=request.retry_delay_seconds,
        expected_recovery=request.expected_recovery,
    )
    
    return JobRetryTestResponse(
        id=test.id,
        job_type=test.job_type,
        failure_point=test.failure_point,
        max_retries=test.max_retries,
        retry_delay_seconds=test.retry_delay_seconds,
        expected_recovery=test.expected_recovery,
        failure_count=test.failure_count,
        success_count=test.success_count,
        final_status=test.final_status,
        attempts=test.attempts,
    )


@router.get("/job-retry-tests", response_model=list[JobRetryTestResponse])
def list_job_retry_tests(current_user: CurrentSuperuser):
    """List all job retry tests."""
    service = get_chaos_testing_service()
    tests = service.list_job_retry_tests()
    
    return [
        JobRetryTestResponse(
            id=t.id,
            job_type=t.job_type,
            failure_point=t.failure_point,
            max_retries=t.max_retries,
            retry_delay_seconds=t.retry_delay_seconds,
            expected_recovery=t.expected_recovery,
            failure_count=t.failure_count,
            success_count=t.success_count,
            final_status=t.final_status,
            attempts=t.attempts,
        )
        for t in tests
    ]


@router.get("/job-retry-tests/{test_id}", response_model=JobRetryTestResponse)
def get_job_retry_test(test_id: str, current_user: CurrentSuperuser):
    """Get a job retry test by ID."""
    service = get_chaos_testing_service()
    test = service.get_job_retry_test(test_id)
    
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job retry test not found",
        )
    
    return JobRetryTestResponse(
        id=test.id,
        job_type=test.job_type,
        failure_point=test.failure_point,
        max_retries=test.max_retries,
        retry_delay_seconds=test.retry_delay_seconds,
        expected_recovery=test.expected_recovery,
        failure_count=test.failure_count,
        success_count=test.success_count,
        final_status=test.final_status,
        attempts=test.attempts,
    )


@router.post(
    "/job-retry-tests/{test_id}/simulate",
    response_model=JobRetryTestResponse,
)
def simulate_job_execution(test_id: str, request: SimulateJobRequest, current_user: CurrentSuperuser):
    """Simulate job execution with failures."""
    service = get_chaos_testing_service()
    
    try:
        test = service.simulate_job_execution(test_id, request.fail_until_attempt)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    
    return JobRetryTestResponse(
        id=test.id,
        job_type=test.job_type,
        failure_point=test.failure_point,
        max_retries=test.max_retries,
        retry_delay_seconds=test.retry_delay_seconds,
        expected_recovery=test.expected_recovery,
        failure_count=test.failure_count,
        success_count=test.success_count,
        final_status=test.final_status,
        attempts=test.attempts,
    )


@router.post(
    "/job-retry-tests/{test_id}/validate",
    response_model=JobRetryValidationResponse,
)
def validate_job_retry(test_id: str, current_user: CurrentSuperuser):
    """Validate job retry behavior."""
    service = get_chaos_testing_service()
    
    try:
        result = service.validate_job_retry_behavior(test_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    
    return JobRetryValidationResponse(**result)


# ===== Degradation Test Endpoints =====


@router.post(
    "/degradation-tests/{scenario_id}",
    response_model=DegradationTestResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_degradation_test(scenario_id: str, current_user: CurrentSuperuser):
    """Create a degradation test for a scenario."""
    service = get_chaos_testing_service()
    
    try:
        test = service.create_degradation_test(scenario_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    
    return DegradationTestResponse(
        id=test.id,
        scenario_id=test.scenario_id,
        expected_level=test.expected_behavior.expected_level.value,
        actual_level=test.actual_level.value if test.actual_level else None,
        fallbacks_triggered=test.fallbacks_triggered,
        passed=test.passed,
        test_duration_ms=test.test_duration_ms,
    )


@router.get("/degradation-tests", response_model=list[DegradationTestResponse])
def list_degradation_tests(current_user: CurrentSuperuser):
    """List all degradation tests."""
    service = get_chaos_testing_service()
    tests = service.list_degradation_tests()
    
    return [
        DegradationTestResponse(
            id=t.id,
            scenario_id=t.scenario_id,
            expected_level=t.expected_behavior.expected_level.value,
            actual_level=t.actual_level.value if t.actual_level else None,
            fallbacks_triggered=t.fallbacks_triggered,
            passed=t.passed,
            test_duration_ms=t.test_duration_ms,
        )
        for t in tests
    ]


@router.post(
    "/degradation-tests/{test_id}/execute",
    response_model=DegradationTestResponse,
)
def execute_degradation_test(test_id: str, current_user: CurrentSuperuser):
    """Execute a degradation test."""
    service = get_chaos_testing_service()
    
    try:
        test = service.execute_degradation_test(test_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    
    return DegradationTestResponse(
        id=test.id,
        scenario_id=test.scenario_id,
        expected_level=test.expected_behavior.expected_level.value,
        actual_level=test.actual_level.value if test.actual_level else None,
        fallbacks_triggered=test.fallbacks_triggered,
        passed=test.passed,
        test_duration_ms=test.test_duration_ms,
    )


# ===== Circuit Breaker Endpoints =====


@router.post(
    "/circuit-breakers",
    response_model=CircuitBreakerResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_circuit_breaker(request: RegisterCircuitBreakerRequest, current_user: CurrentSuperuser):
    """Register a circuit breaker."""
    service = get_chaos_testing_service()
    
    breaker = service.register_circuit_breaker(
        component=request.component,
        recovery_threshold=request.recovery_threshold,
    )
    
    return CircuitBreakerResponse(
        id=breaker.id,
        component=breaker.component,
        state=breaker.state.value,
        failure_count=breaker.failure_count,
        success_count=breaker.success_count,
        half_open_attempts=breaker.half_open_attempts,
        recovery_threshold=breaker.recovery_threshold,
    )


@router.get("/circuit-breakers", response_model=list[CircuitBreakerResponse])
def list_circuit_breakers(current_user: CurrentSuperuser):
    """List all circuit breakers."""
    service = get_chaos_testing_service()
    breakers = service.list_circuit_breakers()
    
    return [
        CircuitBreakerResponse(
            id=b.id,
            component=b.component,
            state=b.state.value,
            failure_count=b.failure_count,
            success_count=b.success_count,
            half_open_attempts=b.half_open_attempts,
            recovery_threshold=b.recovery_threshold,
        )
        for b in breakers
    ]


@router.get("/circuit-breakers/{breaker_id}", response_model=CircuitBreakerResponse)
def get_circuit_breaker(breaker_id: str, current_user: CurrentSuperuser):
    """Get a circuit breaker by ID."""
    service = get_chaos_testing_service()
    breaker = service.get_circuit_breaker(breaker_id)
    
    if not breaker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Circuit breaker not found",
        )
    
    return CircuitBreakerResponse(
        id=breaker.id,
        component=breaker.component,
        state=breaker.state.value,
        failure_count=breaker.failure_count,
        success_count=breaker.success_count,
        half_open_attempts=breaker.half_open_attempts,
        recovery_threshold=breaker.recovery_threshold,
    )


@router.post(
    "/circuit-breakers/{breaker_id}/failure",
    response_model=CircuitBreakerResponse,
)
def record_circuit_failure(breaker_id: str, current_user: CurrentSuperuser):
    """Record a failure for a circuit breaker."""
    service = get_chaos_testing_service()
    
    try:
        breaker = service.record_circuit_breaker_failure(breaker_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    
    return CircuitBreakerResponse(
        id=breaker.id,
        component=breaker.component,
        state=breaker.state.value,
        failure_count=breaker.failure_count,
        success_count=breaker.success_count,
        half_open_attempts=breaker.half_open_attempts,
        recovery_threshold=breaker.recovery_threshold,
    )


@router.post(
    "/circuit-breakers/{breaker_id}/success",
    response_model=CircuitBreakerResponse,
)
def record_circuit_success(breaker_id: str, current_user: CurrentSuperuser):
    """Record a success for a circuit breaker."""
    service = get_chaos_testing_service()
    
    try:
        breaker = service.record_circuit_breaker_success(breaker_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    
    return CircuitBreakerResponse(
        id=breaker.id,
        component=breaker.component,
        state=breaker.state.value,
        failure_count=breaker.failure_count,
        success_count=breaker.success_count,
        half_open_attempts=breaker.half_open_attempts,
        recovery_threshold=breaker.recovery_threshold,
    )


@router.post(
    "/circuit-breakers/{breaker_id}/reset",
    response_model=CircuitBreakerResponse,
)
def attempt_circuit_reset(breaker_id: str, current_user: CurrentSuperuser):
    """Attempt to reset circuit breaker to half-open."""
    service = get_chaos_testing_service()
    
    try:
        breaker = service.attempt_circuit_breaker_reset(breaker_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    
    return CircuitBreakerResponse(
        id=breaker.id,
        component=breaker.component,
        state=breaker.state.value,
        failure_count=breaker.failure_count,
        success_count=breaker.success_count,
        half_open_attempts=breaker.half_open_attempts,
        recovery_threshold=breaker.recovery_threshold,
    )


@router.post(
    "/circuit-breaker-tests",
    response_model=CircuitBreakerTestResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_circuit_breaker_test(request: CreateCircuitBreakerTestRequest, current_user: CurrentSuperuser):
    """Create a circuit breaker test."""
    service = get_chaos_testing_service()
    
    expected_state = validate_circuit_state(request.expected_state_after)
    
    try:
        test = service.create_circuit_breaker_test(
            breaker_id=request.breaker_id,
            injected_failures=request.injected_failures,
            expected_state_after=expected_state,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    
    return CircuitBreakerTestResponse(
        id=test.id,
        component=test.component,
        initial_state=test.initial_state.value,
        injected_failures=test.injected_failures,
        expected_state_after=test.expected_state_after.value,
        actual_state_after=test.actual_state_after.value if test.actual_state_after else None,
        passed=test.passed,
        state_transitions=test.state_transitions,
    )


@router.post(
    "/circuit-breaker-tests/{test_id}/execute/{breaker_id}",
    response_model=CircuitBreakerTestResponse,
)
def execute_circuit_breaker_test(test_id: str, breaker_id: str, current_user: CurrentSuperuser):
    """Execute a circuit breaker test."""
    service = get_chaos_testing_service()
    
    try:
        test = service.execute_circuit_breaker_test(test_id, breaker_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    
    return CircuitBreakerTestResponse(
        id=test.id,
        component=test.component,
        initial_state=test.initial_state.value,
        injected_failures=test.injected_failures,
        expected_state_after=test.expected_state_after.value,
        actual_state_after=test.actual_state_after.value if test.actual_state_after else None,
        passed=test.passed,
        state_transitions=test.state_transitions,
    )


# ===== Test Run Endpoints =====


@router.post(
    "/test-runs",
    response_model=TestRunResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_test_run(request: CreateTestRunRequest, current_user: CurrentSuperuser):
    """Create a new test run."""
    service = get_chaos_testing_service()
    
    run = service.create_test_run(
        name=request.name,
        description=request.description,
        scenario_ids=request.scenario_ids,
    )
    
    return TestRunResponse(
        id=run.id,
        name=run.name,
        description=run.description,
        status=run.status.value,
        total_tests=run.total_tests,
        passed_tests=run.passed_tests,
        failed_tests=run.failed_tests,
        started_at=run.started_at.isoformat() if run.started_at else None,
        completed_at=run.completed_at.isoformat() if run.completed_at else None,
    )


@router.get("/test-runs", response_model=list[TestRunResponse])
def list_test_runs(current_user: CurrentSuperuser):
    """List all test runs."""
    service = get_chaos_testing_service()
    runs = service.list_test_runs()
    
    return [
        TestRunResponse(
            id=r.id,
            name=r.name,
            description=r.description,
            status=r.status.value,
            total_tests=r.total_tests,
            passed_tests=r.passed_tests,
            failed_tests=r.failed_tests,
            started_at=r.started_at.isoformat() if r.started_at else None,
            completed_at=r.completed_at.isoformat() if r.completed_at else None,
        )
        for r in runs
    ]


@router.get("/test-runs/{run_id}", response_model=TestRunResponse)
def get_test_run(run_id: str, current_user: CurrentSuperuser):
    """Get a test run by ID."""
    service = get_chaos_testing_service()
    run = service.get_test_run(run_id)
    
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test run not found",
        )
    
    return TestRunResponse(
        id=run.id,
        name=run.name,
        description=run.description,
        status=run.status.value,
        total_tests=run.total_tests,
        passed_tests=run.passed_tests,
        failed_tests=run.failed_tests,
        started_at=run.started_at.isoformat() if run.started_at else None,
        completed_at=run.completed_at.isoformat() if run.completed_at else None,
    )


@router.post("/test-runs/{run_id}/start", response_model=TestRunResponse)
def start_test_run(run_id: str, current_user: CurrentSuperuser):
    """Start a test run."""
    service = get_chaos_testing_service()
    
    try:
        run = service.start_test_run(run_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    
    return TestRunResponse(
        id=run.id,
        name=run.name,
        description=run.description,
        status=run.status.value,
        total_tests=run.total_tests,
        passed_tests=run.passed_tests,
        failed_tests=run.failed_tests,
        started_at=run.started_at.isoformat() if run.started_at else None,
        completed_at=run.completed_at.isoformat() if run.completed_at else None,
    )


@router.post("/test-runs/{run_id}/abort", response_model=TestRunResponse)
def abort_test_run(run_id: str, current_user: CurrentSuperuser):
    """Abort a running test run."""
    service = get_chaos_testing_service()
    
    try:
        run = service.abort_test_run(run_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    return TestRunResponse(
        id=run.id,
        name=run.name,
        description=run.description,
        status=run.status.value,
        total_tests=run.total_tests,
        passed_tests=run.passed_tests,
        failed_tests=run.failed_tests,
        started_at=run.started_at.isoformat() if run.started_at else None,
        completed_at=run.completed_at.isoformat() if run.completed_at else None,
    )


# ===== Recovery Metrics Endpoints =====


@router.post(
    "/recovery-metrics",
    response_model=RecoveryMetricsResponse,
    status_code=status.HTTP_201_CREATED,
)
def record_recovery_metrics(request: RecordRecoveryMetricsRequest, current_user: CurrentSuperuser):
    """Record recovery metrics for a scenario."""
    service = get_chaos_testing_service()
    
    metrics = service.record_recovery_metrics(
        scenario_id=request.scenario_id,
        detection_time_ms=request.detection_time_ms,
        isolation_time_ms=request.isolation_time_ms,
        recovery_time_ms=request.recovery_time_ms,
        data_loss=request.data_loss,
        data_loss_details=request.data_loss_details,
        requests_affected=request.requests_affected,
        requests_failed=request.requests_failed,
        requests_degraded=request.requests_degraded,
    )
    
    return RecoveryMetricsResponse(
        scenario_id=metrics.scenario_id,
        detection_time_ms=metrics.detection_time_ms,
        isolation_time_ms=metrics.isolation_time_ms,
        recovery_time_ms=metrics.recovery_time_ms,
        data_loss=metrics.data_loss,
        data_loss_details=metrics.data_loss_details,
        requests_affected=metrics.requests_affected,
        requests_failed=metrics.requests_failed,
        requests_degraded=metrics.requests_degraded,
    )


@router.get("/recovery-metrics", response_model=list[RecoveryMetricsResponse])
def list_recovery_metrics(current_user: CurrentSuperuser):
    """List all recovery metrics."""
    service = get_chaos_testing_service()
    metrics = service.list_recovery_metrics()
    
    return [
        RecoveryMetricsResponse(
            scenario_id=m.scenario_id,
            detection_time_ms=m.detection_time_ms,
            isolation_time_ms=m.isolation_time_ms,
            recovery_time_ms=m.recovery_time_ms,
            data_loss=m.data_loss,
            data_loss_details=m.data_loss_details,
            requests_affected=m.requests_affected,
            requests_failed=m.requests_failed,
            requests_degraded=m.requests_degraded,
        )
        for m in metrics
    ]


@router.get("/recovery-metrics/{scenario_id}", response_model=RecoveryMetricsResponse)
def get_recovery_metrics(scenario_id: str, current_user: CurrentSuperuser):
    """Get recovery metrics for a scenario."""
    service = get_chaos_testing_service()
    metrics = service.get_recovery_metrics(scenario_id)
    
    if not metrics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recovery metrics not found",
        )
    
    return RecoveryMetricsResponse(
        scenario_id=metrics.scenario_id,
        detection_time_ms=metrics.detection_time_ms,
        isolation_time_ms=metrics.isolation_time_ms,
        recovery_time_ms=metrics.recovery_time_ms,
        data_loss=metrics.data_loss,
        data_loss_details=metrics.data_loss_details,
        requests_affected=metrics.requests_affected,
        requests_failed=metrics.requests_failed,
        requests_degraded=metrics.requests_degraded,
    )


# ===== Summary Endpoint =====


@router.get("/summary", response_model=ChaosSummaryResponse)
def get_chaos_summary(current_user: CurrentSuperuser):
    """Get chaos testing summary and recommendations."""
    service = get_chaos_testing_service()
    summary = service.get_summary()
    
    return ChaosSummaryResponse(
        total_runs=summary.total_runs,
        completed_runs=summary.completed_runs,
        total_scenarios=summary.total_scenarios,
        total_job_retry_tests=summary.total_job_retry_tests,
        job_retry_pass_rate=summary.job_retry_pass_rate,
        total_degradation_tests=summary.total_degradation_tests,
        degradation_pass_rate=summary.degradation_pass_rate,
        total_circuit_breaker_tests=summary.total_circuit_breaker_tests,
        circuit_breaker_pass_rate=summary.circuit_breaker_pass_rate,
        average_recovery_time_ms=summary.average_recovery_time_ms,
        components_tested=summary.components_tested,
        failure_types_tested=summary.failure_types_tested,
        recommendations=summary.recommendations,
    )


# ===== Maintenance Endpoint =====


@router.delete("/data", status_code=status.HTTP_204_NO_CONTENT)
def clear_all_data(current_user: CurrentSuperuser):
    """Clear all chaos testing data."""
    service = get_chaos_testing_service()
    service.clear_all_data()
