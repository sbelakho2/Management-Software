"""
Tests for Chaos Testing API Endpoints.

Tests REST API for chaos/failure mode testing.
"""

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from sensei.main import app
from sensei.services.utils.chaos_testing import reset_chaos_testing_service


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_service():
    """Reset service before each test."""
    reset_chaos_testing_service()
    yield
    reset_chaos_testing_service()


# ===== Scenario Tests =====


class TestScenarioEndpoints:
    """Tests for scenario endpoints."""
    
    def test_create_scenario(self, client):
        """Test creating a failure scenario."""
        response = client.post(
            "/api/v1/chaos-testing/scenarios",
            json={
                "name": "Storage Outage",
                "description": "Simulate storage failure",
                "failure_type": "storage_down",
                "target_component": "storage",
                "duration_seconds": 60,
                "intensity": 1.0,
            },
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Storage Outage"
        assert data["failure_type"] == "storage_down"
        assert data["target_component"] == "storage"
    
    def test_create_scenario_with_parameters(self, client):
        """Test creating a scenario with custom parameters."""
        response = client.post(
            "/api/v1/chaos-testing/scenarios",
            json={
                "name": "Network Latency",
                "description": "High latency",
                "failure_type": "network_latency",
                "target_component": "api",
                "parameters": {"latency_ms": 5000},
            },
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["parameters"]["latency_ms"] == 5000
    
    def test_create_scenario_invalid_failure_type(self, client):
        """Test creating scenario with invalid failure type."""
        response = client.post(
            "/api/v1/chaos-testing/scenarios",
            json={
                "name": "Test",
                "description": "Test",
                "failure_type": "invalid_type",
                "target_component": "storage",
            },
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_create_scenario_invalid_component(self, client):
        """Test creating scenario with invalid component."""
        response = client.post(
            "/api/v1/chaos-testing/scenarios",
            json={
                "name": "Test",
                "description": "Test",
                "failure_type": "storage_down",
                "target_component": "invalid_component",
            },
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_list_scenarios(self, client):
        """Test listing scenarios."""
        for i in range(3):
            client.post(
                "/api/v1/chaos-testing/scenarios",
                json={
                    "name": f"Scenario {i}",
                    "description": f"Desc {i}",
                    "failure_type": "storage_down",
                    "target_component": "storage",
                },
            )
        
        response = client.get("/api/v1/chaos-testing/scenarios")
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 3
    
    def test_get_scenario(self, client):
        """Test getting a scenario by ID."""
        create_resp = client.post(
            "/api/v1/chaos-testing/scenarios",
            json={
                "name": "Test",
                "description": "Test",
                "failure_type": "database_down",
                "target_component": "database",
            },
        )
        
        scenario_id = create_resp.json()["id"]
        response = client.get(f"/api/v1/chaos-testing/scenarios/{scenario_id}")
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["name"] == "Test"
    
    def test_get_scenario_not_found(self, client):
        """Test getting non-existent scenario."""
        response = client.get("/api/v1/chaos-testing/scenarios/nonexistent")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_delete_scenario(self, client):
        """Test deleting a scenario."""
        create_resp = client.post(
            "/api/v1/chaos-testing/scenarios",
            json={
                "name": "Delete Me",
                "description": "To delete",
                "failure_type": "storage_down",
                "target_component": "storage",
            },
        )
        
        scenario_id = create_resp.json()["id"]
        response = client.delete(f"/api/v1/chaos-testing/scenarios/{scenario_id}")
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify deleted
        get_resp = client.get(f"/api/v1/chaos-testing/scenarios/{scenario_id}")
        assert get_resp.status_code == status.HTTP_404_NOT_FOUND


# ===== Failure Injection Tests =====


class TestFailureInjectionEndpoints:
    """Tests for failure injection endpoints."""
    
    def test_inject_failure(self, client):
        """Test injecting a failure."""
        create_resp = client.post(
            "/api/v1/chaos-testing/scenarios",
            json={
                "name": "Storage Down",
                "description": "Storage failure",
                "failure_type": "storage_down",
                "target_component": "storage",
            },
        )
        
        scenario_id = create_resp.json()["id"]
        response = client.post(f"/api/v1/chaos-testing/failures/{scenario_id}/inject")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["failure_type"] == "storage_down"
        assert data["state"]["storage_available"] is False
    
    def test_inject_failure_not_found(self, client):
        """Test injecting failure for non-existent scenario."""
        response = client.post("/api/v1/chaos-testing/failures/nonexistent/inject")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_remove_failure(self, client):
        """Test removing an injected failure."""
        create_resp = client.post(
            "/api/v1/chaos-testing/scenarios",
            json={
                "name": "Storage Down",
                "description": "Storage failure",
                "failure_type": "storage_down",
                "target_component": "storage",
            },
        )
        
        scenario_id = create_resp.json()["id"]
        client.post(f"/api/v1/chaos-testing/failures/{scenario_id}/inject")
        
        response = client.post(f"/api/v1/chaos-testing/failures/{scenario_id}/remove")
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["state"]["storage_available"] is True
    
    def test_get_active_failures(self, client):
        """Test getting active failures."""
        create_resp = client.post(
            "/api/v1/chaos-testing/scenarios",
            json={
                "name": "Storage Down",
                "description": "Storage failure",
                "failure_type": "storage_down",
                "target_component": "storage",
            },
        )
        
        scenario_id = create_resp.json()["id"]
        client.post(f"/api/v1/chaos-testing/failures/{scenario_id}/inject")
        
        response = client.get("/api/v1/chaos-testing/failures/active")
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 1
    
    def test_get_system_state(self, client):
        """Test getting system state."""
        response = client.get("/api/v1/chaos-testing/state")
        
        assert response.status_code == status.HTTP_200_OK
        state = response.json()
        assert state["storage_available"] is True
        assert state["database_available"] is True


# ===== Job Retry Test Endpoints =====


class TestJobRetryEndpoints:
    """Tests for job retry test endpoints."""
    
    def test_create_job_retry_test(self, client):
        """Test creating a job retry test."""
        response = client.post(
            "/api/v1/chaos-testing/job-retry-tests",
            json={
                "job_type": "pdf_generation",
                "failure_point": "storage_write",
                "max_retries": 3,
                "expected_recovery": True,
            },
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["job_type"] == "pdf_generation"
        assert data["final_status"] == "pending"
    
    def test_list_job_retry_tests(self, client):
        """Test listing job retry tests."""
        for i in range(2):
            client.post(
                "/api/v1/chaos-testing/job-retry-tests",
                json={
                    "job_type": f"job_{i}",
                    "failure_point": f"point_{i}",
                },
            )
        
        response = client.get("/api/v1/chaos-testing/job-retry-tests")
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 2
    
    def test_get_job_retry_test(self, client):
        """Test getting a job retry test."""
        create_resp = client.post(
            "/api/v1/chaos-testing/job-retry-tests",
            json={
                "job_type": "test",
                "failure_point": "test",
            },
        )
        
        test_id = create_resp.json()["id"]
        response = client.get(f"/api/v1/chaos-testing/job-retry-tests/{test_id}")
        
        assert response.status_code == status.HTTP_200_OK
    
    def test_simulate_job_execution(self, client):
        """Test simulating job execution."""
        create_resp = client.post(
            "/api/v1/chaos-testing/job-retry-tests",
            json={
                "job_type": "email_send",
                "failure_point": "smtp",
                "max_retries": 3,
            },
        )
        
        test_id = create_resp.json()["id"]
        response = client.post(
            f"/api/v1/chaos-testing/job-retry-tests/{test_id}/simulate",
            json={"fail_until_attempt": 2},
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["final_status"] == "recovered"
        assert len(data["attempts"]) == 2
    
    def test_validate_job_retry(self, client):
        """Test validating job retry behavior."""
        create_resp = client.post(
            "/api/v1/chaos-testing/job-retry-tests",
            json={
                "job_type": "backup",
                "failure_point": "disk",
                "expected_recovery": True,
            },
        )
        
        test_id = create_resp.json()["id"]
        
        # Simulate first
        client.post(
            f"/api/v1/chaos-testing/job-retry-tests/{test_id}/simulate",
            json={"fail_until_attempt": 2},
        )
        
        response = client.post(
            f"/api/v1/chaos-testing/job-retry-tests/{test_id}/validate"
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["passed"] is True


# ===== Degradation Test Endpoints =====


class TestDegradationEndpoints:
    """Tests for degradation test endpoints."""
    
    def test_create_degradation_test(self, client):
        """Test creating a degradation test."""
        create_resp = client.post(
            "/api/v1/chaos-testing/scenarios",
            json={
                "name": "Storage Down",
                "description": "Storage failure",
                "failure_type": "storage_down",
                "target_component": "storage",
            },
        )
        
        scenario_id = create_resp.json()["id"]
        response = client.post(
            f"/api/v1/chaos-testing/degradation-tests/{scenario_id}"
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["expected_level"] == "read_only"
    
    def test_list_degradation_tests(self, client):
        """Test listing degradation tests."""
        create_resp = client.post(
            "/api/v1/chaos-testing/scenarios",
            json={
                "name": "Test",
                "description": "Test",
                "failure_type": "storage_down",
                "target_component": "storage",
            },
        )
        
        scenario_id = create_resp.json()["id"]
        client.post(f"/api/v1/chaos-testing/degradation-tests/{scenario_id}")
        
        response = client.get("/api/v1/chaos-testing/degradation-tests")
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 1
    
    def test_execute_degradation_test(self, client):
        """Test executing a degradation test."""
        create_resp = client.post(
            "/api/v1/chaos-testing/scenarios",
            json={
                "name": "Storage Down",
                "description": "Storage failure",
                "failure_type": "storage_down",
                "target_component": "storage",
            },
        )
        
        scenario_id = create_resp.json()["id"]
        test_resp = client.post(
            f"/api/v1/chaos-testing/degradation-tests/{scenario_id}"
        )
        
        test_id = test_resp.json()["id"]
        response = client.post(
            f"/api/v1/chaos-testing/degradation-tests/{test_id}/execute"
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["actual_level"] == "read_only"
        assert data["passed"] is True


# ===== Circuit Breaker Endpoints =====


class TestCircuitBreakerEndpoints:
    """Tests for circuit breaker endpoints."""
    
    def test_register_circuit_breaker(self, client):
        """Test registering a circuit breaker."""
        response = client.post(
            "/api/v1/chaos-testing/circuit-breakers",
            json={
                "component": "external_api",
                "recovery_threshold": 5,
            },
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["component"] == "external_api"
        assert data["state"] == "closed"
    
    def test_list_circuit_breakers(self, client):
        """Test listing circuit breakers."""
        for comp in ["api1", "api2"]:
            client.post(
                "/api/v1/chaos-testing/circuit-breakers",
                json={"component": comp},
            )
        
        response = client.get("/api/v1/chaos-testing/circuit-breakers")
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 2
    
    def test_get_circuit_breaker(self, client):
        """Test getting a circuit breaker."""
        create_resp = client.post(
            "/api/v1/chaos-testing/circuit-breakers",
            json={"component": "test"},
        )
        
        breaker_id = create_resp.json()["id"]
        response = client.get(f"/api/v1/chaos-testing/circuit-breakers/{breaker_id}")
        
        assert response.status_code == status.HTTP_200_OK
    
    def test_record_circuit_failure(self, client):
        """Test recording circuit breaker failure."""
        create_resp = client.post(
            "/api/v1/chaos-testing/circuit-breakers",
            json={"component": "test"},
        )
        
        breaker_id = create_resp.json()["id"]
        response = client.post(
            f"/api/v1/chaos-testing/circuit-breakers/{breaker_id}/failure"
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["failure_count"] == 1
    
    def test_record_circuit_success(self, client):
        """Test recording circuit breaker success."""
        create_resp = client.post(
            "/api/v1/chaos-testing/circuit-breakers",
            json={"component": "test"},
        )
        
        breaker_id = create_resp.json()["id"]
        response = client.post(
            f"/api/v1/chaos-testing/circuit-breakers/{breaker_id}/success"
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["success_count"] == 1
    
    def test_circuit_breaker_opens(self, client):
        """Test circuit breaker opens after threshold."""
        create_resp = client.post(
            "/api/v1/chaos-testing/circuit-breakers",
            json={"component": "test"},
        )
        
        breaker_id = create_resp.json()["id"]
        
        # 5 failures should open
        for _ in range(5):
            resp = client.post(
                f"/api/v1/chaos-testing/circuit-breakers/{breaker_id}/failure"
            )
        
        assert resp.json()["state"] == "open"
    
    def test_attempt_circuit_reset(self, client):
        """Test attempting circuit breaker reset."""
        create_resp = client.post(
            "/api/v1/chaos-testing/circuit-breakers",
            json={"component": "test"},
        )
        
        breaker_id = create_resp.json()["id"]
        
        # Open the circuit
        for _ in range(5):
            client.post(
                f"/api/v1/chaos-testing/circuit-breakers/{breaker_id}/failure"
            )
        
        response = client.post(
            f"/api/v1/chaos-testing/circuit-breakers/{breaker_id}/reset"
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["state"] == "half_open"
    
    def test_create_circuit_breaker_test(self, client):
        """Test creating circuit breaker test."""
        create_resp = client.post(
            "/api/v1/chaos-testing/circuit-breakers",
            json={"component": "test"},
        )
        
        breaker_id = create_resp.json()["id"]
        response = client.post(
            "/api/v1/chaos-testing/circuit-breaker-tests",
            json={
                "breaker_id": breaker_id,
                "injected_failures": 5,
                "expected_state_after": "open",
            },
        )
        
        assert response.status_code == status.HTTP_201_CREATED
    
    def test_execute_circuit_breaker_test(self, client):
        """Test executing circuit breaker test."""
        create_resp = client.post(
            "/api/v1/chaos-testing/circuit-breakers",
            json={"component": "test"},
        )
        
        breaker_id = create_resp.json()["id"]
        test_resp = client.post(
            "/api/v1/chaos-testing/circuit-breaker-tests",
            json={
                "breaker_id": breaker_id,
                "injected_failures": 5,
                "expected_state_after": "open",
            },
        )
        
        test_id = test_resp.json()["id"]
        response = client.post(
            f"/api/v1/chaos-testing/circuit-breaker-tests/{test_id}/execute/{breaker_id}"
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["passed"] is True


# ===== Test Run Endpoints =====


class TestTestRunEndpoints:
    """Tests for test run endpoints."""
    
    def test_create_test_run(self, client):
        """Test creating a test run."""
        response = client.post(
            "/api/v1/chaos-testing/test-runs",
            json={
                "name": "Full Chaos Test",
                "description": "Test all failure modes",
            },
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Full Chaos Test"
        assert data["status"] == "pending"
    
    def test_list_test_runs(self, client):
        """Test listing test runs."""
        for i in range(2):
            client.post(
                "/api/v1/chaos-testing/test-runs",
                json={
                    "name": f"Run {i}",
                    "description": f"Desc {i}",
                },
            )
        
        response = client.get("/api/v1/chaos-testing/test-runs")
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 2
    
    def test_get_test_run(self, client):
        """Test getting a test run."""
        create_resp = client.post(
            "/api/v1/chaos-testing/test-runs",
            json={
                "name": "Test",
                "description": "Test",
            },
        )
        
        run_id = create_resp.json()["id"]
        response = client.get(f"/api/v1/chaos-testing/test-runs/{run_id}")
        
        assert response.status_code == status.HTTP_200_OK
    
    def test_start_test_run(self, client):
        """Test starting a test run."""
        # Create scenario first
        scenario_resp = client.post(
            "/api/v1/chaos-testing/scenarios",
            json={
                "name": "Storage",
                "description": "Storage down",
                "failure_type": "storage_down",
                "target_component": "storage",
            },
        )
        
        scenario_id = scenario_resp.json()["id"]
        run_resp = client.post(
            "/api/v1/chaos-testing/test-runs",
            json={
                "name": "Test Run",
                "description": "Test",
                "scenario_ids": [scenario_id],
            },
        )
        
        run_id = run_resp.json()["id"]
        response = client.post(f"/api/v1/chaos-testing/test-runs/{run_id}/start")
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "completed"


# ===== Recovery Metrics Endpoints =====


class TestRecoveryMetricsEndpoints:
    """Tests for recovery metrics endpoints."""
    
    def test_record_recovery_metrics(self, client):
        """Test recording recovery metrics."""
        # Create scenario
        scenario_resp = client.post(
            "/api/v1/chaos-testing/scenarios",
            json={
                "name": "Test",
                "description": "Test",
                "failure_type": "storage_down",
                "target_component": "storage",
            },
        )
        
        scenario_id = scenario_resp.json()["id"]
        response = client.post(
            "/api/v1/chaos-testing/recovery-metrics",
            json={
                "scenario_id": scenario_id,
                "detection_time_ms": 100,
                "isolation_time_ms": 200,
                "recovery_time_ms": 5000,
                "requests_affected": 50,
            },
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["recovery_time_ms"] == 5000
    
    def test_list_recovery_metrics(self, client):
        """Test listing recovery metrics."""
        scenario_resp = client.post(
            "/api/v1/chaos-testing/scenarios",
            json={
                "name": "Test",
                "description": "Test",
                "failure_type": "storage_down",
                "target_component": "storage",
            },
        )
        
        scenario_id = scenario_resp.json()["id"]
        client.post(
            "/api/v1/chaos-testing/recovery-metrics",
            json={
                "scenario_id": scenario_id,
                "detection_time_ms": 100,
                "isolation_time_ms": 200,
                "recovery_time_ms": 5000,
            },
        )
        
        response = client.get("/api/v1/chaos-testing/recovery-metrics")
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 1
    
    def test_get_recovery_metrics(self, client):
        """Test getting recovery metrics for a scenario."""
        scenario_resp = client.post(
            "/api/v1/chaos-testing/scenarios",
            json={
                "name": "Test",
                "description": "Test",
                "failure_type": "storage_down",
                "target_component": "storage",
            },
        )
        
        scenario_id = scenario_resp.json()["id"]
        client.post(
            "/api/v1/chaos-testing/recovery-metrics",
            json={
                "scenario_id": scenario_id,
                "detection_time_ms": 100,
                "isolation_time_ms": 200,
                "recovery_time_ms": 5000,
            },
        )
        
        response = client.get(f"/api/v1/chaos-testing/recovery-metrics/{scenario_id}")
        
        assert response.status_code == status.HTTP_200_OK


# ===== Summary Endpoint =====


class TestSummaryEndpoint:
    """Tests for summary endpoint."""
    
    def test_get_summary_empty(self, client):
        """Test getting summary with no data."""
        response = client.get("/api/v1/chaos-testing/summary")
        
        assert response.status_code == status.HTTP_200_OK
        summary = response.json()
        assert summary["total_runs"] == 0
        assert summary["total_scenarios"] == 0
    
    def test_get_summary_with_data(self, client):
        """Test getting summary with test data."""
        # Create and run scenario
        scenario_resp = client.post(
            "/api/v1/chaos-testing/scenarios",
            json={
                "name": "Storage",
                "description": "Storage down",
                "failure_type": "storage_down",
                "target_component": "storage",
            },
        )
        
        scenario_id = scenario_resp.json()["id"]
        run_resp = client.post(
            "/api/v1/chaos-testing/test-runs",
            json={
                "name": "Test",
                "description": "Test",
                "scenario_ids": [scenario_id],
            },
        )
        
        run_id = run_resp.json()["id"]
        client.post(f"/api/v1/chaos-testing/test-runs/{run_id}/start")
        
        response = client.get("/api/v1/chaos-testing/summary")
        
        assert response.status_code == status.HTTP_200_OK
        summary = response.json()
        assert summary["total_runs"] == 1
        assert summary["completed_runs"] == 1


# ===== Maintenance Endpoint =====


class TestMaintenanceEndpoint:
    """Tests for maintenance endpoints."""
    
    def test_clear_all_data(self, client):
        """Test clearing all data."""
        # Create some data
        client.post(
            "/api/v1/chaos-testing/scenarios",
            json={
                "name": "Test",
                "description": "Test",
                "failure_type": "storage_down",
                "target_component": "storage",
            },
        )
        
        response = client.delete("/api/v1/chaos-testing/data")
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify cleared
        list_resp = client.get("/api/v1/chaos-testing/scenarios")
        assert len(list_resp.json()) == 0
