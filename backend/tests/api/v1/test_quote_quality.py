"""
Tests for Quote Quality Pre-Release Checks API.

Comprehensive tests for quote quality validation endpoints.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from fastapi import status
from fastapi.testclient import TestClient

from sensei.main import app


@pytest.fixture
def client() -> TestClient:
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def valid_quote_data() -> dict:
    """Create valid quote request data."""
    now = datetime.now()
    return {
        "id": str(uuid4()),
        "quote_number": "Q-2025-0001",
        "status": "draft",
        "subtotal": 10000.00,
        "total": 11000.00,
        "total_cost": 7000.00,
        "target_margin": 30.0,
        "actual_margin": 36.36,
        "currency": "USD",
        "valid_from": now.isoformat(),
        "valid_until": (now + timedelta(days=90)).isoformat(),
        "payment_terms": "Net 30",
        "delivery_terms": "FOB Origin",
        "lead_time_days": 14,
        "warranty_terms": "1 year warranty",
        "terms_and_conditions": "Standard T&C apply",
        "rfq_id": str(uuid4()),
        "account_id": str(uuid4()),
        "account_name": "Acme Corp",
        "line_items": [
            {
                "line_number": 1,
                "description": "Widget A",
                "quantity": 10,
                "unit_price": 500.00,
                "total": 5000.00,
            },
            {
                "line_number": 2,
                "description": "Widget B",
                "quantity": 20,
                "unit_price": 250.00,
                "total": 5000.00,
            },
        ],
        "assumptions": [
            {"id": "a1", "text": "Prices based on current supplier quotes"},
            {"id": "a2", "text": "Delivery within continental US"},
        ],
        "supplier_quotes": [
            {
                "supplier_name": "Supplier A",
                "status": "received",
                "valid_until": (now + timedelta(days=60)).isoformat(),
            },
        ],
        "ctq_links": [
            {"id": "c1", "name": "Material Quality", "status": "verified"},
        ],
        "custom_fields": {"project_type": "standard"},
    }


@pytest.fixture
def minimal_quote_data() -> dict:
    """Create minimal quote request data with issues."""
    return {
        "id": str(uuid4()),
        "quote_number": "Q-2025-0002",
        "status": "draft",
    }


# --------------------------------------------------------------------------
# Check Quote Quality Tests
# --------------------------------------------------------------------------

class TestCheckQuoteQuality:
    """Test POST /quote-quality/check endpoint."""
    
    def test_check_valid_quote(self, client: TestClient, valid_quote_data: dict):
        """Test checking a valid quote."""
        response = client.post("/api/v1/quote-quality/check", json=valid_quote_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["quote_id"] == valid_quote_data["id"]
        assert data["quote_number"] == "Q-2025-0001"
        assert data["can_release"] is True
        assert data["error_count"] == 0
        assert "checked_at" in data
        assert "score" in data
        assert data["score"] >= 80.0
        assert len(data["checks"]) > 0
    
    def test_check_invalid_quote(self, client: TestClient, minimal_quote_data: dict):
        """Test checking an invalid quote."""
        response = client.post("/api/v1/quote-quality/check", json=minimal_quote_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["can_release"] is False
        assert data["error_count"] > 0
    
    def test_check_returns_check_details(self, client: TestClient, valid_quote_data: dict):
        """Test that check returns detailed check info."""
        response = client.post("/api/v1/quote-quality/check", json=valid_quote_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Find a specific check
        checks = data["checks"]
        line_items_check = next((c for c in checks if c["check_id"] == "line_items_exist"), None)
        
        assert line_items_check is not None
        assert line_items_check["name"] == "Line Items Present"
        assert line_items_check["category"] == "completeness"
        assert line_items_check["severity"] == "error"
        assert line_items_check["result"] == "pass"


# --------------------------------------------------------------------------
# Check With Config Tests
# --------------------------------------------------------------------------

class TestCheckWithConfig:
    """Test POST /quote-quality/check-with-config endpoint."""
    
    def test_check_with_default_config(self, client: TestClient, valid_quote_data: dict):
        """Test check with default config."""
        response = client.post(
            "/api/v1/quote-quality/check-with-config",
            json={"quote": valid_quote_data},
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["can_release"] is True
    
    def test_check_with_custom_config_stricter_margin(self, client: TestClient, valid_quote_data: dict):
        """Test check with stricter margin requirements."""
        # Make margin barely passing default (36%) but failing custom (40%)
        valid_quote_data["actual_margin"] = 35.0  # Above default 15%, below custom 40%
        
        response = client.post(
            "/api/v1/quote-quality/check-with-config",
            json={
                "quote": valid_quote_data,
                "config": {
                    "min_margin_percent": 40.0,
                    "margin_floor_percent": 30.0,
                },
            },
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Should fail margin check
        margin_check = next((c for c in data["checks"] if c["check_id"] == "margin_target"), None)
        assert margin_check is not None
        assert margin_check["result"] == "fail"
    
    def test_check_with_custom_config_ctq_required(self, client: TestClient, valid_quote_data: dict):
        """Test check with CTQ links required."""
        # Remove CTQ links
        valid_quote_data["ctq_links"] = []
        
        response = client.post(
            "/api/v1/quote-quality/check-with-config",
            json={
                "quote": valid_quote_data,
                "config": {
                    "require_ctq_links": True,
                },
            },
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Should have CTQ warning
        ctq_check = next((c for c in data["checks"] if c["check_id"] == "ctq_links"), None)
        assert ctq_check is not None
        assert ctq_check["result"] == "fail"
    
    def test_check_with_required_custom_fields(self, client: TestClient, valid_quote_data: dict):
        """Test check with required custom fields."""
        # Missing required custom field
        valid_quote_data["custom_fields"] = {"project_type": "standard"}  # Missing "complexity"
        
        response = client.post(
            "/api/v1/quote-quality/check-with-config",
            json={
                "quote": valid_quote_data,
                "config": {
                    "required_custom_fields": ["project_type", "complexity"],
                },
            },
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Should have custom fields warning
        custom_check = next((c for c in data["checks"] if c["check_id"] == "custom_fields"), None)
        assert custom_check is not None
        assert custom_check["result"] == "fail"
        assert "complexity" in custom_check["details"]["missing"]


# --------------------------------------------------------------------------
# Quick Check Tests
# --------------------------------------------------------------------------

class TestQuickCheck:
    """Test POST /quote-quality/quick-check endpoint."""
    
    def test_quick_check_returns_summary(self, client: TestClient, valid_quote_data: dict):
        """Test quick check returns only summary."""
        response = client.post("/api/v1/quote-quality/quick-check", json=valid_quote_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "quote_id" in data
        assert "quote_number" in data
        assert "can_release" in data
        assert "score" in data
        assert "error_count" in data
        assert "warning_count" in data
        # Should NOT have full checks list
        assert "checks" not in data
    
    def test_quick_check_valid_quote(self, client: TestClient, valid_quote_data: dict):
        """Test quick check for valid quote."""
        response = client.post("/api/v1/quote-quality/quick-check", json=valid_quote_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["can_release"] is True
        assert data["error_count"] == 0
    
    def test_quick_check_invalid_quote(self, client: TestClient, minimal_quote_data: dict):
        """Test quick check for invalid quote."""
        response = client.post("/api/v1/quote-quality/quick-check", json=minimal_quote_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["can_release"] is False
        assert data["error_count"] > 0


# --------------------------------------------------------------------------
# Blocking Issues Tests
# --------------------------------------------------------------------------

class TestBlockingIssues:
    """Test POST /quote-quality/blocking-issues endpoint."""
    
    def test_get_blocking_issues_for_valid_quote(self, client: TestClient, valid_quote_data: dict):
        """Test getting blocking issues for valid quote."""
        response = client.post("/api/v1/quote-quality/blocking-issues", json=valid_quote_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["can_release"] is True
        assert data["blocking_count"] == 0
        assert len(data["blocking_issues"]) == 0
    
    def test_get_blocking_issues_for_invalid_quote(self, client: TestClient, minimal_quote_data: dict):
        """Test getting blocking issues for invalid quote."""
        response = client.post("/api/v1/quote-quality/blocking-issues", json=minimal_quote_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["can_release"] is False
        assert data["blocking_count"] > 0
        assert len(data["blocking_issues"]) > 0
        
        # All should be errors
        for issue in data["blocking_issues"]:
            assert issue["severity"] == "error"
            assert issue["result"] == "fail"


# --------------------------------------------------------------------------
# Warnings Tests
# --------------------------------------------------------------------------

class TestWarnings:
    """Test POST /quote-quality/warnings endpoint."""
    
    def test_get_warnings(self, client: TestClient):
        """Test getting warnings."""
        now = datetime.now()
        quote_with_warnings = {
            "id": str(uuid4()),
            "quote_number": "Q-001",
            "status": "draft",
            "subtotal": 1000.00,
            "total": 1100.00,
            "actual_margin": 12.0,  # Below target but above floor
            "valid_until": (now + timedelta(days=60)).isoformat(),
            "payment_terms": None,  # Warning
            "delivery_terms": "FOB",
            "terms_and_conditions": "T&C",
            "line_items": [
                {"line_number": 1, "description": "Item", "quantity": 10, "unit_price": 100.00},
            ],
            "assumptions": [{"id": "a1", "text": "Assumption"}],
        }
        
        response = client.post("/api/v1/quote-quality/warnings", json=quote_with_warnings)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["blocking_count"] > 0
        
        # All should be warnings
        for issue in data["blocking_issues"]:
            assert issue["severity"] == "warning"


# --------------------------------------------------------------------------
# Categories Tests
# --------------------------------------------------------------------------

class TestCategories:
    """Test GET /quote-quality/categories endpoint."""
    
    def test_get_categories(self, client: TestClient):
        """Test getting check categories."""
        response = client.get("/api/v1/quote-quality/categories")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "categories" in data
        categories = data["categories"]
        
        # Check known categories exist
        category_values = [c["value"] for c in categories]
        assert "completeness" in category_values
        assert "pricing" in category_values
        assert "validity" in category_values
        assert "supplier" in category_values
        assert "approval" in category_values
        
        # Check structure
        for cat in categories:
            assert "value" in cat
            assert "name" in cat
            assert "description" in cat


# --------------------------------------------------------------------------
# Severities Tests
# --------------------------------------------------------------------------

class TestSeverities:
    """Test GET /quote-quality/severities endpoint."""
    
    def test_get_severities(self, client: TestClient):
        """Test getting check severities."""
        response = client.get("/api/v1/quote-quality/severities")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "severities" in data
        severities = data["severities"]
        
        # Check all severities exist
        severity_values = [s["value"] for s in severities]
        assert "error" in severity_values
        assert "warning" in severity_values
        assert "info" in severity_values
        
        # Check structure
        for sev in severities:
            assert "value" in sev
            assert "name" in sev
            assert "description" in sev


# --------------------------------------------------------------------------
# Default Config Tests
# --------------------------------------------------------------------------

class TestDefaultConfig:
    """Test GET /quote-quality/default-config endpoint."""
    
    def test_get_default_config(self, client: TestClient):
        """Test getting default configuration."""
        response = client.get("/api/v1/quote-quality/default-config")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "config" in data
        config = data["config"]
        
        # Check known config values
        assert config["min_margin_percent"] == 15.0
        assert config["margin_floor_percent"] == 10.0
        assert config["min_validity_days"] == 30
        assert config["require_at_least_one_line_item"] is True
        assert config["require_assumptions"] is True


# --------------------------------------------------------------------------
# Validate Config Tests
# --------------------------------------------------------------------------

class TestValidateConfig:
    """Test POST /quote-quality/validate-config endpoint."""
    
    def test_validate_valid_config(self, client: TestClient):
        """Test validating a valid configuration."""
        config = {
            "min_margin_percent": 20.0,
            "margin_floor_percent": 10.0,
            "min_validity_days": 30,
            "max_validity_days": 120,
        }
        
        response = client.post("/api/v1/quote-quality/validate-config", json=config)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["valid"] is True
    
    def test_validate_invalid_config_negative_margin(self, client: TestClient):
        """Test validating config with negative margin."""
        config = {
            "min_margin_percent": -5.0,
        }
        
        response = client.post("/api/v1/quote-quality/validate-config", json=config)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_validate_invalid_config_floor_greater_than_target(self, client: TestClient):
        """Test validating config with floor > target."""
        config = {
            "min_margin_percent": 10.0,
            "margin_floor_percent": 20.0,  # Greater than target
        }
        
        response = client.post("/api/v1/quote-quality/validate-config", json=config)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_validate_invalid_config_validity_range(self, client: TestClient):
        """Test validating config with invalid validity range."""
        config = {
            "min_validity_days": 60,
            "max_validity_days": 30,  # Less than min
        }
        
        response = client.post("/api/v1/quote-quality/validate-config", json=config)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# --------------------------------------------------------------------------
# Check Types Tests
# --------------------------------------------------------------------------

class TestCheckTypes:
    """Test GET /quote-quality/check-types endpoint."""
    
    def test_get_check_types(self, client: TestClient):
        """Test getting all check types."""
        response = client.get("/api/v1/quote-quality/check-types")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "checks" in data
        checks = data["checks"]
        
        # Should have many checks
        assert len(checks) > 20
        
        # Check structure
        for check in checks:
            assert "id" in check
            assert "name" in check
            assert "category" in check
        
        # Check known checks exist
        check_ids = [c["id"] for c in checks]
        assert "line_items_exist" in check_ids
        assert "margin_floor" in check_ids
        assert "not_expired" in check_ids
        assert "supplier_quotes_expired" in check_ids


# --------------------------------------------------------------------------
# Integration Tests
# --------------------------------------------------------------------------

class TestIntegration:
    """Integration tests for quote quality API."""
    
    def test_full_workflow(self, client: TestClient, valid_quote_data: dict):
        """Test full validation workflow."""
        # 1. Quick check
        quick_response = client.post("/api/v1/quote-quality/quick-check", json=valid_quote_data)
        assert quick_response.status_code == status.HTTP_200_OK
        quick_data = quick_response.json()
        assert quick_data["can_release"] is True
        
        # 2. Full check
        full_response = client.post("/api/v1/quote-quality/check", json=valid_quote_data)
        assert full_response.status_code == status.HTTP_200_OK
        full_data = full_response.json()
        assert full_data["can_release"] is True
        assert len(full_data["checks"]) > 0
        
        # 3. Get blocking issues
        blocking_response = client.post("/api/v1/quote-quality/blocking-issues", json=valid_quote_data)
        assert blocking_response.status_code == status.HTTP_200_OK
        blocking_data = blocking_response.json()
        assert blocking_data["blocking_count"] == 0
    
    def test_failed_validation_workflow(self, client: TestClient, minimal_quote_data: dict):
        """Test workflow for failed validation."""
        # 1. Quick check
        quick_response = client.post("/api/v1/quote-quality/quick-check", json=minimal_quote_data)
        assert quick_response.status_code == status.HTTP_200_OK
        quick_data = quick_response.json()
        assert quick_data["can_release"] is False
        
        # 2. Get blocking issues to see what needs fixing
        blocking_response = client.post("/api/v1/quote-quality/blocking-issues", json=minimal_quote_data)
        assert blocking_response.status_code == status.HTTP_200_OK
        blocking_data = blocking_response.json()
        assert blocking_data["blocking_count"] > 0
        
        # Each blocking issue should have fix suggestions
        for issue in blocking_data["blocking_issues"]:
            assert issue["fix_suggestion"] is not None or issue["fix_suggestion"] != ""
    
    def test_metadata_endpoints(self, client: TestClient):
        """Test metadata endpoints work together."""
        # Get categories
        categories_response = client.get("/api/v1/quote-quality/categories")
        assert categories_response.status_code == status.HTTP_200_OK
        
        # Get severities
        severities_response = client.get("/api/v1/quote-quality/severities")
        assert severities_response.status_code == status.HTTP_200_OK
        
        # Get check types
        types_response = client.get("/api/v1/quote-quality/check-types")
        assert types_response.status_code == status.HTTP_200_OK
        
        # Get default config
        config_response = client.get("/api/v1/quote-quality/default-config")
        assert config_response.status_code == status.HTTP_200_OK
        
        # Validate the default config
        default_config = config_response.json()["config"]
        validate_response = client.post("/api/v1/quote-quality/validate-config", json=default_config)
        assert validate_response.status_code == status.HTTP_200_OK


# --------------------------------------------------------------------------
# Edge Cases
# --------------------------------------------------------------------------

class TestEdgeCases:
    """Test edge cases."""
    
    def test_expired_quote(self, client: TestClient):
        """Test quote with expired validity."""
        now = datetime.now()
        expired_quote = {
            "id": str(uuid4()),
            "quote_number": "Q-EXPIRED",
            "status": "draft",
            "valid_until": (now - timedelta(days=5)).isoformat(),
            "subtotal": 1000.00,
            "total": 1100.00,
            "line_items": [{"line_number": 1, "description": "Item", "quantity": 1, "unit_price": 1000.00}],
        }
        
        response = client.post("/api/v1/quote-quality/check", json=expired_quote)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["can_release"] is False
        
        # Should have expired check failure
        expired_check = next((c for c in data["checks"] if c["check_id"] == "not_expired"), None)
        assert expired_check is not None
        assert expired_check["result"] == "fail"
        assert expired_check["severity"] == "error"
    
    def test_approval_required_not_approved(self, client: TestClient, valid_quote_data: dict):
        """Test quote requiring approval but not approved."""
        valid_quote_data["requires_approval"] = True
        valid_quote_data["approval_status"] = "pending"
        
        response = client.post("/api/v1/quote-quality/check", json=valid_quote_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["can_release"] is False
        
        # Should have approval check failure
        approval_check = next((c for c in data["checks"] if c["check_id"] == "approval_obtained"), None)
        assert approval_check is not None
        assert approval_check["result"] == "fail"
    
    def test_empty_line_items(self, client: TestClient, valid_quote_data: dict):
        """Test quote with no line items."""
        valid_quote_data["line_items"] = []
        
        response = client.post("/api/v1/quote-quality/check", json=valid_quote_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["can_release"] is False
        
        # Should have line items check failure
        line_check = next((c for c in data["checks"] if c["check_id"] == "line_items_exist"), None)
        assert line_check is not None
        assert line_check["result"] == "fail"
    
    def test_supplier_quote_expired(self, client: TestClient, valid_quote_data: dict):
        """Test quote with expired supplier quote."""
        now = datetime.now()
        valid_quote_data["supplier_quotes"] = [
            {
                "supplier_name": "Expired Supplier",
                "status": "received",
                "valid_until": (now - timedelta(days=10)).isoformat(),
            }
        ]
        
        response = client.post("/api/v1/quote-quality/check", json=valid_quote_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Should have supplier quote expiration check failure
        supplier_check = next((c for c in data["checks"] if c["check_id"] == "supplier_quotes_expired"), None)
        assert supplier_check is not None
        assert supplier_check["result"] == "fail"
        assert supplier_check["severity"] == "error"
