"""
Tests for Escalation Policy API endpoints.

Tests cover:
- Policy listing and retrieval
- Threshold configuration
- Detection endpoints for approvals, risks, and Andons
- Full scan endpoint
- Reference data endpoints
"""

from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from sensei.main import app


client = TestClient(app)
API_PREFIX = "/api/v1/escalation"


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def reference_time() -> datetime:
    """Standard reference time for tests."""
    return datetime(2025, 1, 15, 12, 0, 0)


@pytest.fixture
def sample_approval(reference_time: datetime) -> dict:
    """Create a sample approval payload."""
    return {
        "id": str(uuid4()),
        "name": "Q-2025-001",
        "status": "pending",
        "value": "75000.00",
        "requested_at": (reference_time - timedelta(hours=30)).isoformat(),
        "owner_id": str(uuid4()),
        "owner_name": "John Smith",
        "current_escalation_level": None,
        "account_name": "ACME Corp",
    }


@pytest.fixture
def sample_risk(reference_time: datetime) -> dict:
    """Create a sample risk payload."""
    return {
        "id": str(uuid4()),
        "risk_number": "R-2025-001",
        "title": "Supply chain disruption",
        "status": "mitigating",
        "risk_level": "high",
        "inherent_risk_score": 15,
        "residual_risk_score": 12,
        "risk_owner_id": str(uuid4()),
        "risk_owner_name": "Jane Doe",
        "target_resolution_date": (reference_time + timedelta(days=10)).isoformat(),
        "identified_date": (reference_time - timedelta(days=5)).isoformat(),
        "category": "supply_chain",
        "current_escalation_level": None,
    }


@pytest.fixture
def sample_andon(reference_time: datetime) -> dict:
    """Create a sample Andon payload."""
    return {
        "id": 1001,
        "andon_number": "A-2025-001",
        "description": "Machine breakdown on line 1",
        "status": "open",
        "severity": "red",
        "reported_at": (reference_time - timedelta(minutes=10)).isoformat(),
        "acknowledged_at": None,
        "station_id": 101,
        "station_name": "Line 1 - Station A",
        "red_ack_minutes": 5,
        "yellow_ack_minutes": 15,
        "current_escalation_level": None,
        "assigned_to_id": str(uuid4()),
        "assigned_to_name": "Bob Technician",
    }


# ==============================================================================
# Policy Endpoints Tests
# ==============================================================================

class TestPolicyEndpoints:
    """Test policy listing and retrieval."""
    
    def test_list_policies(self):
        """List all escalation policies."""
        response = client.get(f"{API_PREFIX}/policies")
        
        assert response.status_code == status.HTTP_200_OK
        policies = response.json()
        assert isinstance(policies, list)
        assert len(policies) >= 4
        
        # Check policy structure
        policy_names = [p["name"] for p in policies]
        assert "approval_aging" in policy_names
        assert "high_severity_risk" in policy_names
    
    def test_get_policy(self):
        """Get a specific policy."""
        response = client.get(f"{API_PREFIX}/policies/approval_aging")
        
        assert response.status_code == status.HTTP_200_OK
        policy = response.json()
        assert policy["name"] == "approval_aging"
        assert policy["target_type"] == "quote_approval"
        assert "escalation_levels" in policy
        assert len(policy["escalation_levels"]) > 0
    
    def test_get_nonexistent_policy(self):
        """Get a policy that doesn't exist returns 404."""
        response = client.get(f"{API_PREFIX}/policies/nonexistent")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ==============================================================================
# Threshold Endpoints Tests
# ==============================================================================

class TestThresholdEndpoints:
    """Test threshold configuration endpoints."""
    
    def test_get_thresholds(self):
        """Get current thresholds."""
        response = client.get(f"{API_PREFIX}/thresholds")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "approval_thresholds" in data
        assert "risk_thresholds" in data
        assert "l1" in data["approval_thresholds"]
        assert "hours" in data["approval_thresholds"]["l1"]
    
    def test_update_approval_threshold_hours(self):
        """Update approval threshold hours."""
        response = client.put(
            f"{API_PREFIX}/thresholds/approval",
            json={"level": "l1", "hours": 12},
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "updated"
    
    def test_update_approval_threshold_value(self):
        """Update approval threshold value."""
        response = client.put(
            f"{API_PREFIX}/thresholds/approval",
            json={"level": "l2", "value": "75000.00"},
        )
        
        assert response.status_code == status.HTTP_200_OK
    
    def test_update_approval_threshold_invalid_level(self):
        """Invalid level returns 400."""
        response = client.put(
            f"{API_PREFIX}/thresholds/approval",
            json={"level": "invalid", "hours": 12},
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_update_risk_threshold(self):
        """Update risk threshold."""
        response = client.put(
            f"{API_PREFIX}/thresholds/risk",
            json={"severity": "medium", "escalation_level": "l2"},
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "updated"
    
    def test_update_risk_threshold_invalid_severity(self):
        """Invalid severity returns 400."""
        response = client.put(
            f"{API_PREFIX}/thresholds/risk",
            json={"severity": "invalid", "escalation_level": "l1"},
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ==============================================================================
# Detection Endpoints Tests
# ==============================================================================

class TestDetectionEndpoints:
    """Test detection endpoints."""
    
    def test_detect_aging_approvals(self, sample_approval: dict, reference_time: datetime):
        """Detect aging approvals."""
        response = client.post(
            f"{API_PREFIX}/detect/approvals/aging",
            json={
                "approvals": [sample_approval],
                "reference_time": reference_time.isoformat(),
            },
        )
        
        assert response.status_code == status.HTTP_200_OK
        result = response.json()
        assert result["policy_name"] == "approval_aging"
        assert result["total_evaluated"] == 1
        assert result["items_escalated"] == 1
        assert result["items"][0]["reason"] == "approval_aging"
    
    def test_detect_value_based_approvals(self, sample_approval: dict, reference_time: datetime):
        """Detect value-based approvals."""
        sample_approval["value"] = "150000.00"
        
        response = client.post(
            f"{API_PREFIX}/detect/approvals/value",
            json={"approvals": [sample_approval]},
        )
        
        assert response.status_code == status.HTTP_200_OK
        result = response.json()
        assert result["items_escalated"] == 1
        assert result["items"][0]["reason"] == "approval_value_threshold"
    
    def test_detect_high_severity_risks(self, sample_risk: dict, reference_time: datetime):
        """Detect high-severity risks."""
        response = client.post(
            f"{API_PREFIX}/detect/risks/severity",
            json={
                "risks": [sample_risk],
                "reference_time": reference_time.isoformat(),
            },
        )
        
        assert response.status_code == status.HTTP_200_OK
        result = response.json()
        assert result["items_escalated"] == 1
        assert result["items"][0]["current_level"] == "l2"
    
    def test_detect_overdue_risks(self, sample_risk: dict, reference_time: datetime):
        """Detect overdue risks."""
        sample_risk["target_resolution_date"] = (
            reference_time - timedelta(days=10)
        ).isoformat()
        
        response = client.post(
            f"{API_PREFIX}/detect/risks/overdue",
            json={
                "risks": [sample_risk],
                "reference_time": reference_time.isoformat(),
            },
        )
        
        assert response.status_code == status.HTTP_200_OK
        result = response.json()
        assert result["items_escalated"] == 1
        assert result["items"][0]["days_overdue"] == 10
    
    def test_detect_andon_sla_breaches(self, sample_andon: dict, reference_time: datetime):
        """Detect Andon SLA breaches."""
        response = client.post(
            f"{API_PREFIX}/detect/andons/sla-breach",
            json={
                "andons": [sample_andon],
                "reference_time": reference_time.isoformat(),
            },
        )
        
        assert response.status_code == status.HTTP_200_OK
        result = response.json()
        assert result["items_escalated"] == 1
        assert result["items"][0]["reason"] == "andon_sla_breach"
    
    def test_detect_with_empty_list(self, reference_time: datetime):
        """Detection with empty list returns zero items."""
        response = client.post(
            f"{API_PREFIX}/detect/approvals/aging",
            json={
                "approvals": [],
                "reference_time": reference_time.isoformat(),
            },
        )
        
        assert response.status_code == status.HTTP_200_OK
        result = response.json()
        assert result["items_escalated"] == 0


# ==============================================================================
# Full Scan Endpoint Tests
# ==============================================================================

class TestFullScanEndpoint:
    """Test full scan endpoint."""
    
    def test_full_scan(
        self,
        sample_approval: dict,
        sample_risk: dict,
        sample_andon: dict,
        reference_time: datetime,
    ):
        """Run a full escalation scan."""
        response = client.post(
            f"{API_PREFIX}/detect/full-scan",
            json={
                "approvals": [sample_approval],
                "risks": [sample_risk],
                "andons": [sample_andon],
                "reference_time": reference_time.isoformat(),
            },
        )
        
        assert response.status_code == status.HTTP_200_OK
        result = response.json()
        
        assert result["total_evaluated"] > 0
        assert result["total_escalated"] > 0
        assert "by_policy" in result
        assert "approval_aging" in result["by_policy"]
    
    def test_full_scan_partial(self, sample_approval: dict, reference_time: datetime):
        """Run a partial scan with only some entity types."""
        response = client.post(
            f"{API_PREFIX}/detect/full-scan",
            json={
                "approvals": [sample_approval],
                "reference_time": reference_time.isoformat(),
            },
        )
        
        assert response.status_code == status.HTTP_200_OK
        result = response.json()
        
        # Should have approval results but not risk or andon
        assert "approval_aging" in result["by_policy"]


# ==============================================================================
# Reference Data Endpoints Tests
# ==============================================================================

class TestReferenceDataEndpoints:
    """Test reference data endpoints."""
    
    def test_get_target_types(self):
        """Get all target types."""
        response = client.get(f"{API_PREFIX}/target-types")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert all("value" in item and "label" in item for item in data)
        
        values = [item["value"] for item in data]
        assert "quote_approval" in values
        assert "risk" in values
    
    def test_get_escalation_reasons(self):
        """Get all escalation reasons."""
        response = client.get(f"{API_PREFIX}/reasons")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        
        values = [item["value"] for item in data]
        assert "approval_aging" in values
        assert "risk_severity_critical" in values
    
    def test_get_escalation_levels(self):
        """Get all escalation levels."""
        response = client.get(f"{API_PREFIX}/levels")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 4  # L1-L4
        
        # Check structure
        assert all("value" in item and "label" in item and "description" in item for item in data)
    
    def test_get_escalation_priorities(self):
        """Get all escalation priorities."""
        response = client.get(f"{API_PREFIX}/priorities")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 5  # low, normal, high, urgent, critical
    
    def test_get_escalation_statuses(self):
        """Get all escalation statuses."""
        response = client.get(f"{API_PREFIX}/statuses")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) >= 5
        
        values = [item["value"] for item in data]
        assert "pending" in values
        assert "resolved" in values
    
    def test_get_target_role(self):
        """Get target role for a level and type."""
        response = client.get(f"{API_PREFIX}/target-role/l2/quote_approval")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["level"] == "l2"
        assert data["target_type"] == "quote_approval"
        assert "role" in data
    
    def test_get_target_role_invalid_level(self):
        """Invalid level returns 400."""
        response = client.get(f"{API_PREFIX}/target-role/invalid/quote_approval")
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_get_target_role_invalid_type(self):
        """Invalid target type returns 400."""
        response = client.get(f"{API_PREFIX}/target-role/l1/invalid")
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ==============================================================================
# Response Structure Tests
# ==============================================================================

class TestResponseStructure:
    """Test response structure and serialization."""
    
    def test_escalation_item_structure(self, sample_approval: dict, reference_time: datetime):
        """Verify escalation item response structure."""
        response = client.post(
            f"{API_PREFIX}/detect/approvals/aging",
            json={
                "approvals": [sample_approval],
                "reference_time": reference_time.isoformat(),
            },
        )
        
        assert response.status_code == status.HTTP_200_OK
        result = response.json()
        
        if result["items_escalated"] > 0:
            item = result["items"][0]
            
            # Required fields
            assert "entity_id" in item
            assert "entity_type" in item
            assert "entity_name" in item
            assert "reason" in item
            assert "priority" in item
            assert "current_level" in item
            assert "context" in item
    
    def test_policy_response_structure(self):
        """Verify policy response structure."""
        response = client.get(f"{API_PREFIX}/policies/approval_aging")
        
        assert response.status_code == status.HTTP_200_OK
        policy = response.json()
        
        assert "name" in policy
        assert "description" in policy
        assert "target_type" in policy
        assert "enabled" in policy
        assert "conditions" in policy
        assert "escalation_levels" in policy
        
        # Check escalation level structure
        if policy["escalation_levels"]:
            level = policy["escalation_levels"][0]
            assert "level" in level
            assert "wait_hours" in level
            assert "notification_channels" in level
