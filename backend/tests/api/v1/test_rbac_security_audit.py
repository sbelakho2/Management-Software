"""
Tests for RBAC Security Audit API Endpoints.

Tests REST API for security auditing of RBAC and Audit Logs.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from sensei.main import app
from sensei.services.core.rbac_security_audit import reset_rbac_security_audit_service


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_service():
    """Reset service before each test."""
    reset_rbac_security_audit_service()
    yield
    reset_rbac_security_audit_service()


def iso_now() -> str:
    """Get current time in ISO format."""
    return datetime.now(timezone.utc).isoformat()


# ===== Role Registration Tests =====


class TestRoleEndpoints:
    """Tests for role registration endpoints."""
    
    def test_register_role(self, client):
        """Test registering a role."""
        role_id = str(uuid4())
        
        response = client.post(
            "/api/v1/security-audit/roles",
            json={
                "role_id": role_id,
                "name": "admin",
                "display_name": "Administrator",
                "role_type": "admin",
                "is_system": True,
                "hierarchy_level": 10,
                "permission_count": 25,
                "user_count": 2,
            },
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["id"] == role_id
        assert data["name"] == "admin"
        assert data["is_system"] is True
    
    def test_get_roles(self, client):
        """Test getting all roles."""
        # Register roles
        for i in range(3):
            client.post(
                "/api/v1/security-audit/roles",
                json={
                    "role_id": str(uuid4()),
                    "name": f"role{i}",
                    "display_name": f"Role {i}",
                },
            )
        
        response = client.get("/api/v1/security-audit/roles")
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 3
    
    def test_get_role_by_id(self, client):
        """Test getting a role by ID."""
        role_id = str(uuid4())
        
        client.post(
            "/api/v1/security-audit/roles",
            json={
                "role_id": role_id,
                "name": "test",
                "display_name": "Test Role",
            },
        )
        
        response = client.get(f"/api/v1/security-audit/roles/{role_id}")
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["name"] == "test"
    
    def test_get_role_not_found(self, client):
        """Test getting a non-existent role."""
        fake_id = str(uuid4())
        response = client.get(f"/api/v1/security-audit/roles/{fake_id}")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ===== Permission Registration Tests =====


class TestPermissionEndpoints:
    """Tests for permission registration endpoints."""
    
    def test_register_permission(self, client):
        """Test registering a permission."""
        perm_id = str(uuid4())
        
        response = client.post(
            "/api/v1/security-audit/permissions",
            json={
                "permission_id": perm_id,
                "name": "quotes:create",
                "display_name": "Create Quotes",
                "resource": "quotes",
                "action": "create",
                "is_system": True,
                "role_count": 3,
            },
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["resource"] == "quotes"
        assert data["action"] == "create"
    
    def test_get_permissions(self, client):
        """Test getting all permissions."""
        for i in range(2):
            client.post(
                "/api/v1/security-audit/permissions",
                json={
                    "permission_id": str(uuid4()),
                    "name": f"res{i}:action{i}",
                    "display_name": f"Permission {i}",
                    "resource": f"res{i}",
                    "action": f"action{i}",
                },
            )
        
        response = client.get("/api/v1/security-audit/permissions")
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 2


# ===== User-Role Assignment Tests =====


class TestUserRoleEndpoints:
    """Tests for user-role assignment endpoints."""
    
    def test_register_user_role(self, client):
        """Test registering a user-role assignment."""
        response = client.post(
            "/api/v1/security-audit/user-roles",
            json={
                "user_id": str(uuid4()),
                "user_email": "user@test.com",
                "role_id": str(uuid4()),
                "role_name": "admin",
                "assigned_at": iso_now(),
                "is_active": True,
            },
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["role_name"] == "admin"
        assert data["is_expired"] is False
    
    def test_get_user_roles(self, client):
        """Test getting all user-role assignments."""
        for i in range(3):
            client.post(
                "/api/v1/security-audit/user-roles",
                json={
                    "user_id": str(uuid4()),
                    "user_email": f"user{i}@test.com",
                    "role_id": str(uuid4()),
                    "role_name": f"role{i}",
                    "assigned_at": iso_now(),
                },
            )
        
        response = client.get("/api/v1/security-audit/user-roles")
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 3
    
    def test_get_user_role_assignments(self, client):
        """Test getting roles for a specific user."""
        user_id = str(uuid4())
        
        # Register two roles for same user
        for role_name in ["admin", "viewer"]:
            client.post(
                "/api/v1/security-audit/user-roles",
                json={
                    "user_id": user_id,
                    "user_email": "user@test.com",
                    "role_id": str(uuid4()),
                    "role_name": role_name,
                    "assigned_at": iso_now(),
                },
            )
        
        response = client.get(f"/api/v1/security-audit/user-roles/{user_id}")
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 2


# ===== Audit Log Tests =====


class TestAuditLogEndpoints:
    """Tests for audit log endpoints."""
    
    def test_register_audit_log(self, client):
        """Test registering an audit log entry."""
        response = client.post(
            "/api/v1/security-audit/audit-logs",
            json={
                "log_id": str(uuid4()),
                "entity_type": "quotes",
                "entity_id": str(uuid4()),
                "action": "create",
                "created_at": iso_now(),
                "user_id": str(uuid4()),
                "user_email": "user@test.com",
                "has_new_values": True,
            },
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["entity_type"] == "quotes"
        assert data["action"] == "create"
    
    def test_get_audit_logs(self, client):
        """Test getting audit logs."""
        for i in range(3):
            client.post(
                "/api/v1/security-audit/audit-logs",
                json={
                    "log_id": str(uuid4()),
                    "entity_type": "quotes",
                    "entity_id": str(uuid4()),
                    "action": "create",
                    "created_at": iso_now(),
                },
            )
        
        response = client.get("/api/v1/security-audit/audit-logs")
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 3
    
    def test_get_audit_logs_filtered(self, client):
        """Test filtering audit logs."""
        # Create logs with different entity types
        client.post(
            "/api/v1/security-audit/audit-logs",
            json={
                "log_id": str(uuid4()),
                "entity_type": "quotes",
                "entity_id": str(uuid4()),
                "action": "create",
                "created_at": iso_now(),
            },
        )
        client.post(
            "/api/v1/security-audit/audit-logs",
            json={
                "log_id": str(uuid4()),
                "entity_type": "users",
                "entity_id": str(uuid4()),
                "action": "update",
                "created_at": iso_now(),
            },
        )
        
        response = client.get("/api/v1/security-audit/audit-logs?entity_type=quotes")
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 1


# ===== Access Pattern Tests =====


class TestAccessPatternEndpoints:
    """Tests for access pattern endpoints."""
    
    def test_record_access_pattern(self, client):
        """Test recording an access pattern."""
        response = client.post(
            "/api/v1/security-audit/access-patterns",
            json={
                "user_id": str(uuid4()),
                "user_email": "user@test.com",
                "action": "read",
                "resource": "quotes",
                "access_time": iso_now(),
            },
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["resource"] == "quotes"
        assert data["count"] == 1
    
    def test_get_access_patterns(self, client):
        """Test getting access patterns."""
        user_id = str(uuid4())
        
        for _ in range(5):
            client.post(
                "/api/v1/security-audit/access-patterns",
                json={
                    "user_id": user_id,
                    "user_email": "user@test.com",
                    "action": "read",
                    "resource": "quotes",
                    "access_time": iso_now(),
                },
            )
        
        response = client.get("/api/v1/security-audit/access-patterns")
        
        assert response.status_code == status.HTTP_200_OK
        patterns = response.json()
        assert len(patterns) == 1
        assert patterns[0]["count"] == 5


# ===== Verification Tests =====


class TestVerificationEndpoints:
    """Tests for verification endpoints."""
    
    def test_verify_role_configuration(self, client):
        """Test role configuration verification."""
        # Register role without permissions
        client.post(
            "/api/v1/security-audit/roles",
            json={
                "role_id": str(uuid4()),
                "name": "empty",
                "display_name": "Empty Role",
                "permission_count": 0,
            },
        )
        
        response = client.post("/api/v1/security-audit/verify/roles")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["check_name"] == "role_configuration"
        assert data["findings_count"] >= 1
    
    def test_verify_permission_configuration(self, client):
        """Test permission configuration verification."""
        # Register unused permission
        client.post(
            "/api/v1/security-audit/permissions",
            json={
                "permission_id": str(uuid4()),
                "name": "unused:perm",
                "display_name": "Unused",
                "resource": "unused",
                "action": "perm",
                "role_count": 0,
            },
        )
        
        response = client.post("/api/v1/security-audit/verify/permissions")
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["findings_count"] >= 1
    
    def test_verify_user_assignments(self, client):
        """Test user assignment verification."""
        user_id = str(uuid4())
        
        # Self-assigned role
        client.post(
            "/api/v1/security-audit/user-roles",
            json={
                "user_id": user_id,
                "user_email": "self@test.com",
                "role_id": str(uuid4()),
                "role_name": "admin",
                "assigned_at": iso_now(),
                "assigned_by_id": user_id,  # Self-assigned
            },
        )
        
        response = client.post("/api/v1/security-audit/verify/user-assignments")
        
        assert response.status_code == status.HTTP_200_OK
        findings = response.json()["findings"]
        critical = [f for f in findings if f["severity"] == "critical"]
        assert len(critical) >= 1
    
    def test_verify_audit_logs(self, client):
        """Test audit log verification."""
        # Anonymous log
        client.post(
            "/api/v1/security-audit/audit-logs",
            json={
                "log_id": str(uuid4()),
                "entity_type": "quotes",
                "entity_id": str(uuid4()),
                "action": "create",
                "created_at": iso_now(),
                "user_id": None,
            },
        )
        
        response = client.post("/api/v1/security-audit/verify/audit-logs")
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["findings_count"] >= 1
    
    def test_detect_access_anomalies(self, client):
        """Test access anomaly detection."""
        now = datetime.now(timezone.utc)
        # Off-hours access (3 AM)
        off_hours = now.replace(hour=3).isoformat()
        
        client.post(
            "/api/v1/security-audit/access-patterns",
            json={
                "user_id": str(uuid4()),
                "user_email": "night@test.com",
                "action": "read",
                "resource": "quotes",
                "access_time": off_hours,
            },
        )
        
        response = client.post("/api/v1/security-audit/verify/access-patterns")
        
        assert response.status_code == status.HTTP_200_OK
        # Should detect off-hours access
        findings = response.json()["findings"]
        off_hour = [f for f in findings if "off-hours" in f["title"].lower()]
        assert len(off_hour) >= 1


# ===== Findings Tests =====


class TestFindingsEndpoints:
    """Tests for findings endpoints."""
    
    def test_get_findings(self, client):
        """Test getting all findings."""
        # Generate findings by creating problematic config
        client.post(
            "/api/v1/security-audit/roles",
            json={
                "role_id": str(uuid4()),
                "name": "empty",
                "display_name": "Empty",
                "permission_count": 0,
            },
        )
        client.post("/api/v1/security-audit/verify/roles")
        
        response = client.get("/api/v1/security-audit/findings")
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) >= 1
    
    def test_get_findings_filtered_by_severity(self, client):
        """Test filtering findings by severity."""
        user_id = str(uuid4())
        
        # Create critical finding (self-assigned)
        client.post(
            "/api/v1/security-audit/user-roles",
            json={
                "user_id": user_id,
                "user_email": "self@test.com",
                "role_id": str(uuid4()),
                "role_name": "admin",
                "assigned_at": iso_now(),
                "assigned_by_id": user_id,
            },
        )
        client.post("/api/v1/security-audit/verify/user-assignments")
        
        response = client.get("/api/v1/security-audit/findings?severity=critical")
        
        assert response.status_code == status.HTTP_200_OK
        findings = response.json()
        assert all(f["severity"] == "critical" for f in findings)
    
    def test_get_findings_summary(self, client):
        """Test getting findings summary."""
        client.post(
            "/api/v1/security-audit/roles",
            json={
                "role_id": str(uuid4()),
                "name": "empty",
                "display_name": "Empty",
                "permission_count": 0,
            },
        )
        client.post("/api/v1/security-audit/verify/roles")
        
        response = client.get("/api/v1/security-audit/findings/summary")
        
        assert response.status_code == status.HTTP_200_OK
        summary = response.json()
        assert "critical" in summary
        assert "high" in summary
        assert "medium" in summary
    
    def test_resolve_finding(self, client):
        """Test resolving a finding."""
        # Generate a finding
        client.post(
            "/api/v1/security-audit/roles",
            json={
                "role_id": str(uuid4()),
                "name": "empty",
                "display_name": "Empty",
                "permission_count": 0,
            },
        )
        client.post("/api/v1/security-audit/verify/roles")
        
        findings_response = client.get("/api/v1/security-audit/findings")
        finding_id = findings_response.json()[0]["id"]
        
        # Resolve it
        response = client.post(
            f"/api/v1/security-audit/findings/{finding_id}/resolve",
            json={"resolved_by": "admin@test.com"},
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["resolved"] is True
        assert response.json()["resolved_by"] == "admin@test.com"
    
    def test_resolve_finding_not_found(self, client):
        """Test resolving a non-existent finding."""
        response = client.post(
            "/api/v1/security-audit/findings/INVALID-ID/resolve",
            json={"resolved_by": "admin@test.com"},
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ===== Compliance Report Tests =====


class TestComplianceReportEndpoint:
    """Tests for compliance report generation."""
    
    def test_generate_compliance_report(self, client):
        """Test generating a compliance report."""
        # Set up some data
        client.post(
            "/api/v1/security-audit/roles",
            json={
                "role_id": str(uuid4()),
                "name": "viewer",
                "display_name": "Viewer",
                "permission_count": 5,
            },
        )
        
        response = client.post("/api/v1/security-audit/report")
        
        assert response.status_code == status.HTTP_200_OK
        report = response.json()
        
        assert "report_id" in report
        assert "status" in report
        assert "total_checks" in report
        assert "findings" in report
        assert "recommendations" in report
        assert "role_summary" in report
    
    def test_compliance_report_shows_non_compliant(self, client):
        """Test that report shows non-compliant with critical issues."""
        user_id = str(uuid4())
        
        # Create critical issue (self-assigned role)
        client.post(
            "/api/v1/security-audit/user-roles",
            json={
                "user_id": user_id,
                "user_email": "self@test.com",
                "role_id": str(uuid4()),
                "role_name": "admin",
                "assigned_at": iso_now(),
                "assigned_by_id": user_id,
            },
        )
        
        response = client.post("/api/v1/security-audit/report")
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "non_compliant"


# ===== Maintenance Tests =====


class TestMaintenanceEndpoints:
    """Tests for maintenance endpoints."""
    
    def test_clear_all_data(self, client):
        """Test clearing all data."""
        # Add some data
        client.post(
            "/api/v1/security-audit/roles",
            json={
                "role_id": str(uuid4()),
                "name": "test",
                "display_name": "Test",
            },
        )
        
        # Clear it
        response = client.delete("/api/v1/security-audit/data")
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify empty
        roles_response = client.get("/api/v1/security-audit/roles")
        assert len(roles_response.json()) == 0


# ===== Validation Tests =====


class TestValidation:
    """Tests for input validation."""
    
    def test_invalid_uuid(self, client):
        """Test invalid UUID handling."""
        response = client.post(
            "/api/v1/security-audit/roles",
            json={
                "role_id": "not-a-uuid",
                "name": "test",
                "display_name": "Test",
            },
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_invalid_severity_filter(self, client):
        """Test invalid severity filter."""
        response = client.get("/api/v1/security-audit/findings?severity=invalid")
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_invalid_category_filter(self, client):
        """Test invalid category filter."""
        response = client.get("/api/v1/security-audit/findings?category=invalid")
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
