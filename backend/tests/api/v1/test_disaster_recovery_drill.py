"""
Tests for Disaster Recovery Drill API endpoints.

Tests all API endpoints for:
- RPO/RTO target management
- Drill configuration management
- Schedule management
- Drill execution
- Results and compliance reporting
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from sensei.main import app
from sensei.api.deps import get_token_data
from sensei.core.security import TokenData
from sensei.services.core.disaster_recovery_drill import reset_dr_drill_service


def _mock_admin_token() -> TokenData:
    """Return a fake admin TokenData so router-level auth is satisfied."""
    return TokenData(
        sub=str(uuid4()),
        type="access",
        exp=datetime.now(timezone.utc) + timedelta(hours=1),
        iat=datetime.now(timezone.utc),
        jti=str(uuid4()),
        roles=["admin"],
        permissions=[],
    )


@pytest.fixture
def client():
    """Create a test client with admin auth overridden."""
    reset_dr_drill_service()
    app.dependency_overrides[get_token_data] = _mock_admin_token
    yield TestClient(app)
    app.dependency_overrides.pop(get_token_data, None)
    reset_dr_drill_service()


# ===== Target Management Tests =====


class TestTargetEndpoints:
    """Tests for RPO/RTO target endpoints."""
    
    def test_get_rpo_targets(self, client: TestClient):
        """Test getting default RPO targets."""
        response = client.get("/api/v1/dr-drills/targets/rpo")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 3
        assert any(t["target_name"] == "database_critical" for t in data)
    
    def test_create_rpo_target(self, client: TestClient):
        """Test creating an RPO target."""
        response = client.post(
            "/api/v1/dr-drills/targets/rpo",
            json={
                "target_name": "custom_target",
                "recovery_target": "database",
                "max_data_loss_minutes": 30,
                "description": "Custom target",
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["target_name"] == "custom_target"
        assert data["max_data_loss_minutes"] == 30
    
    def test_create_rpo_target_invalid(self, client: TestClient):
        """Test creating RPO target with invalid data."""
        response = client.post(
            "/api/v1/dr-drills/targets/rpo",
            json={
                "target_name": "invalid",
                "recovery_target": "database",
                "max_data_loss_minutes": 0,  # Invalid
            },
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_get_rto_targets(self, client: TestClient):
        """Test getting default RTO targets."""
        response = client.get("/api/v1/dr-drills/targets/rto")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 3
    
    def test_create_rto_target(self, client: TestClient):
        """Test creating an RTO target."""
        response = client.post(
            "/api/v1/dr-drills/targets/rto",
            json={
                "target_name": "custom_rto",
                "recovery_target": "application_state",
                "max_recovery_minutes": 15,
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["target_name"] == "custom_rto"
        assert data["max_recovery_minutes"] == 15


# ===== Configuration Tests =====


class TestConfigurationEndpoints:
    """Tests for configuration endpoints."""
    
    def test_create_configuration(self, client: TestClient):
        """Test creating a drill configuration."""
        response = client.post(
            "/api/v1/dr-drills/configurations",
            json={
                "name": "Full Database Restore",
                "description": "Monthly full restore test",
                "drill_type": "full_restore",
                "recovery_target": "database",
                "rpo_target_minutes": 15,
                "rto_target_minutes": 30,
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Full Database Restore"
        assert data["drill_type"] == "full_restore"
        assert data["id"] is not None
    
    def test_list_configurations(self, client: TestClient):
        """Test listing configurations."""
        # Create configs
        for i in range(3):
            client.post(
                "/api/v1/dr-drills/configurations",
                json={
                    "name": f"Config {i}",
                    "description": "Test",
                    "drill_type": "full_restore",
                    "recovery_target": "database",
                },
            )
        
        response = client.get("/api/v1/dr-drills/configurations")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
    
    def test_get_configuration(self, client: TestClient):
        """Test getting a configuration by ID."""
        create_resp = client.post(
            "/api/v1/dr-drills/configurations",
            json={
                "name": "Test Config",
                "description": "Test",
                "drill_type": "full_restore",
                "recovery_target": "database",
            },
        )
        config_id = create_resp.json()["id"]
        
        response = client.get(f"/api/v1/dr-drills/configurations/{config_id}")
        
        assert response.status_code == 200
        assert response.json()["name"] == "Test Config"
    
    def test_get_configuration_not_found(self, client: TestClient):
        """Test getting non-existent configuration."""
        response = client.get("/api/v1/dr-drills/configurations/nonexistent")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data.get("detail", {}).get("message", "") or "not found" in data.get("message", "")
    
    def test_delete_configuration(self, client: TestClient):
        """Test deleting a configuration."""
        create_resp = client.post(
            "/api/v1/dr-drills/configurations",
            json={
                "name": "Delete Me",
                "description": "Test",
                "drill_type": "full_restore",
                "recovery_target": "database",
            },
        )
        config_id = create_resp.json()["id"]
        
        response = client.delete(f"/api/v1/dr-drills/configurations/{config_id}")
        
        assert response.status_code == 204
        
        # Verify deleted
        get_resp = client.get(f"/api/v1/dr-drills/configurations/{config_id}")
        assert get_resp.status_code == 404


# ===== Schedule Tests =====


class TestScheduleEndpoints:
    """Tests for schedule endpoints."""
    
    def test_create_schedule(self, client: TestClient):
        """Test creating a schedule."""
        # Create config first
        config_resp = client.post(
            "/api/v1/dr-drills/configurations",
            json={
                "name": "Test",
                "description": "Test",
                "drill_type": "full_restore",
                "recovery_target": "database",
            },
        )
        config_id = config_resp.json()["id"]
        
        response = client.post(
            "/api/v1/dr-drills/schedules",
            json={
                "configuration_id": config_id,
                "frequency": "weekly",
                "time_of_day": "02:00",
                "day_of_week": 0,
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["frequency"] == "weekly"
        assert data["is_active"] is True
    
    def test_create_schedule_invalid_frequency(self, client: TestClient):
        """Test creating schedule with invalid frequency."""
        config_resp = client.post(
            "/api/v1/dr-drills/configurations",
            json={
                "name": "Test",
                "description": "Test",
                "drill_type": "full_restore",
                "recovery_target": "database",
            },
        )
        config_id = config_resp.json()["id"]
        
        response = client.post(
            "/api/v1/dr-drills/schedules",
            json={
                "configuration_id": config_id,
                "frequency": "hourly",  # Invalid
            },
        )
        
        assert response.status_code == 400
    
    def test_list_schedules(self, client: TestClient):
        """Test listing schedules."""
        config_resp = client.post(
            "/api/v1/dr-drills/configurations",
            json={
                "name": "Test",
                "description": "Test",
                "drill_type": "full_restore",
                "recovery_target": "database",
            },
        )
        config_id = config_resp.json()["id"]
        
        for freq in ["daily", "weekly", "monthly"]:
            client.post(
                "/api/v1/dr-drills/schedules",
                json={"configuration_id": config_id, "frequency": freq},
            )
        
        response = client.get("/api/v1/dr-drills/schedules")
        
        assert response.status_code == 200
        assert len(response.json()) == 3
    
    def test_toggle_schedule(self, client: TestClient):
        """Test toggling a schedule."""
        config_resp = client.post(
            "/api/v1/dr-drills/configurations",
            json={
                "name": "Test",
                "description": "Test",
                "drill_type": "full_restore",
                "recovery_target": "database",
            },
        )
        config_id = config_resp.json()["id"]
        
        schedule_resp = client.post(
            "/api/v1/dr-drills/schedules",
            json={"configuration_id": config_id, "frequency": "daily"},
        )
        schedule_id = schedule_resp.json()["id"]
        
        response = client.patch(
            f"/api/v1/dr-drills/schedules/{schedule_id}",
            json={"is_active": False},
        )
        
        assert response.status_code == 200
        assert response.json()["is_active"] is False
    
    def test_delete_schedule(self, client: TestClient):
        """Test deleting a schedule."""
        config_resp = client.post(
            "/api/v1/dr-drills/configurations",
            json={
                "name": "Test",
                "description": "Test",
                "drill_type": "full_restore",
                "recovery_target": "database",
            },
        )
        config_id = config_resp.json()["id"]
        
        schedule_resp = client.post(
            "/api/v1/dr-drills/schedules",
            json={"configuration_id": config_id, "frequency": "daily"},
        )
        schedule_id = schedule_resp.json()["id"]
        
        response = client.delete(f"/api/v1/dr-drills/schedules/{schedule_id}")
        
        assert response.status_code == 204


# ===== Drill Execution Tests =====


class TestExecutionEndpoints:
    """Tests for drill execution endpoints."""
    
    def test_start_drill(self, client: TestClient):
        """Test starting a drill."""
        config_resp = client.post(
            "/api/v1/dr-drills/configurations",
            json={
                "name": "Full Restore",
                "description": "Test",
                "drill_type": "full_restore",
                "recovery_target": "database",
            },
        )
        config_id = config_resp.json()["id"]
        
        response = client.post(
            "/api/v1/dr-drills/executions",
            json={
                "configuration_id": config_id,
                "executed_by": "admin",
                "notes": "Monthly drill",
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "in_progress"
        assert data["configuration_name"] == "Full Restore"
        assert len(data["steps"]) > 0
    
    def test_start_drill_config_not_found(self, client: TestClient):
        """Test starting drill for non-existent config."""
        response = client.post(
            "/api/v1/dr-drills/executions",
            json={"configuration_id": "nonexistent"},
        )
        
        assert response.status_code == 400
    
    def test_list_executions(self, client: TestClient):
        """Test listing executions."""
        config_resp = client.post(
            "/api/v1/dr-drills/configurations",
            json={
                "name": "Test",
                "description": "Test",
                "drill_type": "full_restore",
                "recovery_target": "database",
            },
        )
        config_id = config_resp.json()["id"]
        
        for _ in range(3):
            client.post(
                "/api/v1/dr-drills/executions",
                json={"configuration_id": config_id},
            )
        
        response = client.get("/api/v1/dr-drills/executions")
        
        assert response.status_code == 200
        assert len(response.json()) == 3
    
    def test_get_execution(self, client: TestClient):
        """Test getting an execution by ID."""
        config_resp = client.post(
            "/api/v1/dr-drills/configurations",
            json={
                "name": "Test",
                "description": "Test",
                "drill_type": "full_restore",
                "recovery_target": "database",
            },
        )
        config_id = config_resp.json()["id"]
        
        exec_resp = client.post(
            "/api/v1/dr-drills/executions",
            json={"configuration_id": config_id},
        )
        exec_id = exec_resp.json()["id"]
        
        response = client.get(f"/api/v1/dr-drills/executions/{exec_id}")
        
        assert response.status_code == 200
        assert response.json()["id"] == exec_id
    
    def test_execute_step(self, client: TestClient):
        """Test executing a drill step."""
        config_resp = client.post(
            "/api/v1/dr-drills/configurations",
            json={
                "name": "Test",
                "description": "Test",
                "drill_type": "full_restore",
                "recovery_target": "database",
            },
        )
        config_id = config_resp.json()["id"]
        
        exec_resp = client.post(
            "/api/v1/dr-drills/executions",
            json={"configuration_id": config_id},
        )
        exec_data = exec_resp.json()
        exec_id = exec_data["id"]
        step_id = exec_data["steps"][0]["id"]
        
        response = client.post(
            f"/api/v1/dr-drills/executions/{exec_id}/steps/{step_id}/execute",
            json={
                "success": True,
                "output": {"rows_restored": 1000},
            },
        )
        
        assert response.status_code == 200
        assert response.json()["status"] == "completed"
    
    def test_complete_drill(self, client: TestClient):
        """Test completing a drill."""
        config_resp = client.post(
            "/api/v1/dr-drills/configurations",
            json={
                "name": "Test",
                "description": "Test",
                "drill_type": "full_restore",
                "recovery_target": "database",
                "rpo_target_minutes": 120,
                "rto_target_minutes": 120,
            },
        )
        config_id = config_resp.json()["id"]
        
        exec_resp = client.post(
            "/api/v1/dr-drills/executions",
            json={"configuration_id": config_id},
        )
        exec_id = exec_resp.json()["id"]
        
        response = client.post(
            f"/api/v1/dr-drills/executions/{exec_id}/complete",
            json={"data_verified": True},
        )
        
        assert response.status_code == 200
        assert response.json()["status"] == "completed"
        assert response.json()["data_verified"] is True
    
    def test_fail_drill(self, client: TestClient):
        """Test failing a drill."""
        config_resp = client.post(
            "/api/v1/dr-drills/configurations",
            json={
                "name": "Test",
                "description": "Test",
                "drill_type": "full_restore",
                "recovery_target": "database",
            },
        )
        config_id = config_resp.json()["id"]
        
        exec_resp = client.post(
            "/api/v1/dr-drills/executions",
            json={"configuration_id": config_id},
        )
        exec_id = exec_resp.json()["id"]
        
        response = client.post(
            f"/api/v1/dr-drills/executions/{exec_id}/fail",
            json={"error_message": "Backup corrupted"},
        )
        
        assert response.status_code == 200
        assert response.json()["status"] == "failed"
    
    def test_cancel_drill(self, client: TestClient):
        """Test cancelling a drill."""
        config_resp = client.post(
            "/api/v1/dr-drills/configurations",
            json={
                "name": "Test",
                "description": "Test",
                "drill_type": "full_restore",
                "recovery_target": "database",
            },
        )
        config_id = config_resp.json()["id"]
        
        exec_resp = client.post(
            "/api/v1/dr-drills/executions",
            json={"configuration_id": config_id},
        )
        exec_id = exec_resp.json()["id"]
        
        response = client.post(f"/api/v1/dr-drills/executions/{exec_id}/cancel")
        
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"


# ===== Results and Reporting Tests =====


class TestReportingEndpoints:
    """Tests for results and reporting endpoints."""
    
    def test_get_drill_result(self, client: TestClient):
        """Test getting drill result."""
        config_resp = client.post(
            "/api/v1/dr-drills/configurations",
            json={
                "name": "Test",
                "description": "Test",
                "drill_type": "full_restore",
                "recovery_target": "database",
                "rpo_target_minutes": 120,
                "rto_target_minutes": 120,
            },
        )
        config_id = config_resp.json()["id"]
        
        exec_resp = client.post(
            "/api/v1/dr-drills/executions",
            json={"configuration_id": config_id},
        )
        exec_id = exec_resp.json()["id"]
        
        client.post(
            f"/api/v1/dr-drills/executions/{exec_id}/complete",
            json={"data_verified": True},
        )
        
        response = client.get(f"/api/v1/dr-drills/executions/{exec_id}/result")
        
        assert response.status_code == 200
        data = response.json()
        assert data["execution_id"] == exec_id
        assert data["status"] == "completed"
        assert data["data_integrity_verified"] is True
    
    def test_get_compliance_report(self, client: TestClient):
        """Test getting compliance report."""
        # Create and run some drills
        config_resp = client.post(
            "/api/v1/dr-drills/configurations",
            json={
                "name": "Test",
                "description": "Test",
                "drill_type": "full_restore",
                "recovery_target": "database",
                "rpo_target_minutes": 120,
                "rto_target_minutes": 120,
            },
        )
        config_id = config_resp.json()["id"]
        
        for _ in range(3):
            exec_resp = client.post(
                "/api/v1/dr-drills/executions",
                json={"configuration_id": config_id},
            )
            exec_id = exec_resp.json()["id"]
            client.post(
                f"/api/v1/dr-drills/executions/{exec_id}/complete",
                json={"data_verified": True},
            )
        
        response = client.get("/api/v1/dr-drills/compliance-report")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_drills"] == 3
        assert data["successful_drills"] == 3
        assert "recommendations" in data
        assert "report_id" in data


# ===== Enumeration Tests =====


class TestEnumerationEndpoints:
    """Tests for enumeration endpoints."""
    
    def test_list_recovery_targets(self, client: TestClient):
        """Test listing recovery targets."""
        response = client.get("/api/v1/dr-drills/recovery-targets")
        
        assert response.status_code == 200
        data = response.json()
        assert "database" in data
        assert "full_system" in data
    
    def test_list_drill_types(self, client: TestClient):
        """Test listing drill types."""
        response = client.get("/api/v1/dr-drills/drill-types")
        
        assert response.status_code == 200
        data = response.json()
        assert "full_restore" in data
        assert "failover" in data
    
    def test_list_drill_statuses(self, client: TestClient):
        """Test listing drill statuses."""
        response = client.get("/api/v1/dr-drills/drill-statuses")
        
        assert response.status_code == 200
        data = response.json()
        assert "in_progress" in data
        assert "completed" in data
    
    def test_list_compliance_levels(self, client: TestClient):
        """Test listing compliance levels."""
        response = client.get("/api/v1/dr-drills/compliance-levels")
        
        assert response.status_code == 200
        data = response.json()
        assert "compliant" in data
        assert "non_compliant" in data


# ===== Maintenance Tests =====


class TestMaintenanceEndpoints:
    """Tests for maintenance endpoints."""
    
    def test_clear_all_data(self, client: TestClient):
        """Test clearing all data."""
        # Create some data
        config_resp = client.post(
            "/api/v1/dr-drills/configurations",
            json={
                "name": "Test",
                "description": "Test",
                "drill_type": "full_restore",
                "recovery_target": "database",
            },
        )
        config_id = config_resp.json()["id"]
        
        client.post(
            "/api/v1/dr-drills/schedules",
            json={"configuration_id": config_id, "frequency": "daily"},
        )
        
        response = client.delete("/api/v1/dr-drills/data")
        
        assert response.status_code == 204
        
        # Verify data cleared
        configs = client.get("/api/v1/dr-drills/configurations")
        assert len(configs.json()) == 0
    
    def test_reset_service(self, client: TestClient):
        """Test resetting the service."""
        response = client.post("/api/v1/dr-drills/reset")
        
        assert response.status_code == 204
