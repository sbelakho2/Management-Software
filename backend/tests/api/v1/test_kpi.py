"""
Tests for KPI Metrics API endpoints.
"""

import pytest
from datetime import date, datetime, timedelta
from fastapi.testclient import TestClient

from sensei.main import app
from sensei.api.v1.endpoints.kpi import _service, _muda_lesson_engine


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_service():
    """Reset service state between tests."""
    # Store original state
    original_definitions = _service._definitions.copy()
    original_values = {k: list(v) for k, v in _service._values.items()}
    original_dashboards = _service._dashboards.copy()
    original_deliveries = list(_muda_lesson_engine.deliveries)
    
    yield
    
    # Restore original state
    _service._definitions = original_definitions
    _service._values = original_values
    _service._dashboards = original_dashboards
    _muda_lesson_engine.deliveries = original_deliveries


# --------------------------------------------------------------------------
# Definition Tests
# --------------------------------------------------------------------------

class TestDefinitionEndpoints:
    """Tests for KPI definition CRUD endpoints."""
    
    def test_create_definition(self, client):
        """Test creating a KPI definition."""
        response = client.post(
            "/api/v1/kpi/definitions",
            json={
                "name": "Test KPI",
                "description": "A test KPI",
                "category": "custom",
                "unit": "percentage",
                "direction": "higher_is_better",
                "threshold": {
                    "target": 90.0,
                    "warning_threshold": 10.0,
                    "critical_threshold": 20.0,
                },
                "tags": ["test"],
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test KPI"
        assert data["category"] == "custom"
        assert data["threshold"]["target"] == 90.0
    
    def test_create_definition_with_id(self, client):
        """Test creating a definition with specified ID."""
        response = client.post(
            "/api/v1/kpi/definitions",
            json={
                "id": "custom-kpi-1",
                "name": "Custom KPI",
                "description": "Custom",
                "category": "quality",
                "unit": "count",
                "direction": "lower_is_better",
            },
        )
        
        assert response.status_code == 201
        assert response.json()["id"] == "custom-kpi-1"
    
    def test_list_definitions(self, client):
        """Test listing KPI definitions."""
        response = client.get("/api/v1/kpi/definitions")
        
        assert response.status_code == 200
        data = response.json()
        # Should have default KPIs
        assert len(data) > 0
    
    def test_list_definitions_by_category(self, client):
        """Test filtering definitions by category."""
        response = client.get("/api/v1/kpi/definitions?category=quoting")
        
        assert response.status_code == 200
        data = response.json()
        for d in data:
            assert d["category"] == "quoting"
    
    def test_list_definitions_by_tags(self, client):
        """Test filtering definitions by tags."""
        response = client.get("/api/v1/kpi/definitions?tags=phase1")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
    
    def test_get_default_kpis(self, client):
        """Test getting default KPI IDs."""
        response = client.get("/api/v1/kpi/definitions/defaults")
        
        assert response.status_code == 200
        data = response.json()
        assert "rfq-completeness" in data
        assert "oee" in data
    
    def test_get_definition(self, client):
        """Test getting a specific definition."""
        response = client.get("/api/v1/kpi/definitions/rfq-completeness")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "rfq-completeness"
        assert data["name"] == "RFQ Completeness Score"
    
    def test_get_definition_not_found(self, client):
        """Test getting non-existent definition."""
        response = client.get("/api/v1/kpi/definitions/non-existent")
        
        assert response.status_code == 404
    
    def test_update_definition(self, client):
        """Test updating a definition."""
        # Create first
        client.post(
            "/api/v1/kpi/definitions",
            json={
                "id": "update-test",
                "name": "Update Test",
                "description": "Original",
                "category": "custom",
                "unit": "percentage",
                "direction": "higher_is_better",
            },
        )
        
        response = client.put(
            "/api/v1/kpi/definitions/update-test",
            json={"name": "Updated Name", "description": "Updated description"},
        )
        
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"
    
    def test_delete_definition(self, client):
        """Test deleting a definition."""
        # Create first
        client.post(
            "/api/v1/kpi/definitions",
            json={
                "id": "delete-test",
                "name": "Delete Test",
                "description": "To delete",
                "category": "custom",
                "unit": "count",
                "direction": "higher_is_better",
            },
        )
        
        response = client.delete("/api/v1/kpi/definitions/delete-test")
        
        assert response.status_code == 204
    
    def test_delete_default_kpi_fails(self, client):
        """Test that default KPIs cannot be deleted."""
        response = client.delete("/api/v1/kpi/definitions/rfq-completeness")
        
        assert response.status_code == 400


# --------------------------------------------------------------------------
# Value Tests
# --------------------------------------------------------------------------

class TestValueEndpoints:
    """Tests for KPI value endpoints."""
    
    def test_record_value(self, client):
        """Test recording a KPI value."""
        response = client.post(
            "/api/v1/kpi/values",
            json={
                "kpi_id": "rfq-completeness",
                "value": 87.5,
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["kpi_id"] == "rfq-completeness"
        assert data["value"] == 87.5
        assert data["status"] in ["green", "yellow", "on_target", "within_tolerance"]
    
    def test_record_value_with_dimensions(self, client):
        """Test recording a value with dimensions."""
        response = client.post(
            "/api/v1/kpi/values",
            json={
                "kpi_id": "rfq-completeness",
                "value": 92.0,
                "dimensions": {"segment": "automotive"},
            },
        )
        
        assert response.status_code == 201
        assert response.json()["dimensions"]["segment"] == "automotive"
    
    def test_record_value_with_period(self, client):
        """Test recording a value with period dates."""
        today = date.today().isoformat()
        week_ago = (date.today() - timedelta(days=7)).isoformat()
        
        response = client.post(
            "/api/v1/kpi/values",
            json={
                "kpi_id": "rfq-completeness",
                "value": 90.0,
                "period_start": week_ago,
                "period_end": today,
            },
        )
        
        assert response.status_code == 201
        assert response.json()["period_start"] == week_ago
    
    def test_get_latest_value(self, client):
        """Test getting the latest value."""
        # Record some values
        for val in [85.0, 88.0, 92.0]:
            client.post(
                "/api/v1/kpi/values",
                json={"kpi_id": "rfq-completeness", "value": val},
            )
        
        response = client.get("/api/v1/kpi/values/rfq-completeness/latest")
        
        assert response.status_code == 200
        assert response.json()["value"] == 92.0
    
    def test_get_latest_value_not_found(self, client):
        """Test getting latest value when none exists."""
        # Use a custom KPI with no values
        client.post(
            "/api/v1/kpi/definitions",
            json={
                "id": "no-values",
                "name": "No Values",
                "description": "Test",
                "category": "custom",
                "unit": "count",
                "direction": "higher_is_better",
            },
        )
        
        response = client.get("/api/v1/kpi/values/no-values/latest")
        
        assert response.status_code == 200
        assert response.json() is None
    
    def test_get_values(self, client):
        """Test getting values list."""
        # Record values
        for i in range(5):
            client.post(
                "/api/v1/kpi/values",
                json={"kpi_id": "rfq-completeness", "value": 80.0 + i},
            )
        
        response = client.get("/api/v1/kpi/values/rfq-completeness")
        
        assert response.status_code == 200
        assert len(response.json()) >= 5
    
    def test_get_values_with_limit(self, client):
        """Test limiting values returned."""
        # Record values
        for i in range(10):
            client.post(
                "/api/v1/kpi/values",
                json={"kpi_id": "rfq-completeness", "value": 80.0 + i},
            )
        
        response = client.get("/api/v1/kpi/values/rfq-completeness?limit=5")
        
        assert response.status_code == 200
        assert len(response.json()) == 5


# --------------------------------------------------------------------------
# Calculation Tests
# --------------------------------------------------------------------------

class TestCalculationEndpoints:
    """Tests for KPI calculation endpoints."""
    
    def test_calculate_kpi(self, client):
        """Test calculating a KPI without data sources fails gracefully.
        
        In production, KPI calculation requires actual data sources.
        Without configured data, the calculator should return an error.
        """
        today = date.today().isoformat()
        week_ago = (date.today() - timedelta(days=7)).isoformat()
        
        response = client.post(
            "/api/v1/kpi/calculate",
            json={
                "kpi_id": "oee",
                "start_date": week_ago,
                "end_date": today,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        # Without component data, OEE calculation should fail with an error
        assert data["success"] is False
        assert data["error"] is not None
        assert data["calculation_time_ms"] >= 0
    
    def test_calculate_kpi_not_found(self, client):
        """Test calculating non-existent KPI."""
        today = date.today().isoformat()
        
        response = client.post(
            "/api/v1/kpi/calculate",
            json={
                "kpi_id": "non-existent",
                "start_date": today,
                "end_date": today,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "not found" in data["error"]
    
    def test_calculate_kpi_with_dimensions(self, client):
        """Test calculating KPI with dimensions without data fails gracefully."""
        today = date.today().isoformat()
        week_ago = (date.today() - timedelta(days=7)).isoformat()
        
        response = client.post(
            "/api/v1/kpi/calculate",
            json={
                "kpi_id": "rfq-completeness",
                "start_date": week_ago,
                "end_date": today,
                "dimensions": {"segment": "aerospace"},
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        # Without data source, calculation should fail
        assert data["success"] is False
        assert data["error"] is not None
    
    def test_calculate_batch(self, client):
        """Test calculating multiple KPIs fails gracefully without data."""
        today = date.today().isoformat()
        week_ago = (date.today() - timedelta(days=7)).isoformat()
        
        response = client.post(
            f"/api/v1/kpi/calculate-batch?start_date={week_ago}&end_date={today}",
            json=["rfq-completeness", "oee", "training-compliance"],
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        # Without data sources, all calculations should fail
        assert all(not r["success"] for r in data)


# --------------------------------------------------------------------------
# Trend Tests
# --------------------------------------------------------------------------

class TestTrendEndpoints:
    """Tests for trend analysis endpoints."""
    
    def test_analyze_trend(self, client):
        """Test analyzing KPI trend."""
        # First record some values to analyze
        today = date.today()
        for i in range(14):
            client.post(
                "/api/v1/kpi/values",
                json={
                    "kpi_id": "rfq-completeness",
                    "value": 80.0 + i,
                    "timestamp": (datetime.now() - timedelta(days=13-i)).isoformat(),
                },
            )
        
        response = client.get(
            f"/api/v1/kpi/trends/rfq-completeness"
            f"?start_date={(today - timedelta(days=6)).isoformat()}"
            f"&end_date={today.isoformat()}"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data is not None
        assert data["kpi_id"] == "rfq-completeness"
        assert "direction" in data
    
    def test_analyze_trend_no_data(self, client):
        """Test trend analysis with no data."""
        # Create a KPI with no values
        client.post(
            "/api/v1/kpi/definitions",
            json={
                "id": "trend-no-data",
                "name": "No Data",
                "description": "Test",
                "category": "custom",
                "unit": "percentage",
                "direction": "higher_is_better",
            },
        )
        
        today = date.today()
        response = client.get(
            f"/api/v1/kpi/trends/trend-no-data"
            f"?start_date={(today - timedelta(days=7)).isoformat()}"
            f"&end_date={today.isoformat()}"
        )
        
        assert response.status_code == 200
        data = response.json()
        if data:
            assert data["direction"] == "insufficient_data"


# --------------------------------------------------------------------------
# Dashboard Tests
# --------------------------------------------------------------------------

class TestDashboardEndpoints:
    """Tests for dashboard endpoints."""
    
    def test_create_dashboard(self, client):
        """Test creating a dashboard."""
        response = client.post(
            "/api/v1/kpi/dashboards",
            json={
                "name": "Test Dashboard",
                "description": "A test dashboard",
                "kpi_ids": ["rfq-completeness", "quote-cycle-time"],
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Dashboard"
        assert len(data["kpi_ids"]) == 2
    
    def test_create_dashboard_with_id(self, client):
        """Test creating a dashboard with specified ID."""
        response = client.post(
            "/api/v1/kpi/dashboards",
            json={
                "id": "custom-dashboard",
                "name": "Custom Dashboard",
                "description": "Custom",
                "kpi_ids": ["oee"],
            },
        )
        
        assert response.status_code == 201
        assert response.json()["id"] == "custom-dashboard"
    
    def test_list_dashboards(self, client):
        """Test listing dashboards."""
        response = client.get("/api/v1/kpi/dashboards")
        
        assert response.status_code == 200
        data = response.json()
        # Should have default dashboards
        assert len(data) >= 5
    
    def test_list_dashboards_by_owner(self, client):
        """Test filtering dashboards by owner."""
        # Create owned dashboard
        client.post(
            "/api/v1/kpi/dashboards",
            json={
                "id": "owned-dash",
                "name": "Owned",
                "description": "Test",
                "owner_id": "user-1",
                "is_public": False,
            },
        )
        
        response = client.get(
            "/api/v1/kpi/dashboards?owner_id=user-1&include_public=false"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert all(d["owner_id"] == "user-1" for d in data)
    
    def test_get_default_dashboards(self, client):
        """Test getting default dashboard IDs."""
        response = client.get("/api/v1/kpi/dashboards/defaults")
        
        assert response.status_code == 200
        data = response.json()
        assert "quote-to-cash" in data
        assert "executive" in data
    
    def test_get_dashboard(self, client):
        """Test getting a specific dashboard."""
        response = client.get("/api/v1/kpi/dashboards/quote-to-cash")
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Quote-to-Cash Performance"
    
    def test_get_dashboard_not_found(self, client):
        """Test getting non-existent dashboard."""
        response = client.get("/api/v1/kpi/dashboards/non-existent")
        
        assert response.status_code == 404
    
    def test_update_dashboard(self, client):
        """Test updating a dashboard."""
        # Create first
        client.post(
            "/api/v1/kpi/dashboards",
            json={
                "id": "update-dash",
                "name": "Original",
                "description": "Test",
            },
        )
        
        response = client.put(
            "/api/v1/kpi/dashboards/update-dash",
            json={"name": "Updated Dashboard"},
        )
        
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Dashboard"
    
    def test_delete_dashboard(self, client):
        """Test deleting a dashboard."""
        # Create first
        client.post(
            "/api/v1/kpi/dashboards",
            json={
                "id": "delete-dash",
                "name": "Delete Me",
                "description": "Test",
            },
        )
        
        response = client.delete("/api/v1/kpi/dashboards/delete-dash")
        
        assert response.status_code == 204
    
    def test_delete_default_dashboard_fails(self, client):
        """Test that default dashboards cannot be deleted."""
        response = client.delete("/api/v1/kpi/dashboards/quote-to-cash")
        
        assert response.status_code == 400
    
    def test_get_dashboard_data(self, client):
        """Test getting dashboard data."""
        today = date.today().isoformat()
        month_ago = (date.today() - timedelta(days=30)).isoformat()
        
        response = client.get(
            f"/api/v1/kpi/dashboards/quote-to-cash/data"
            f"?start_date={month_ago}&end_date={today}"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "dashboard" in data
        assert "period" in data
        assert "kpis" in data


# --------------------------------------------------------------------------
# Metadata Tests
# --------------------------------------------------------------------------

class TestMetadataEndpoints:
    """Tests for metadata endpoints."""
    
    def test_get_categories(self, client):
        """Test getting KPI categories."""
        response = client.get("/api/v1/kpi/categories")
        
        assert response.status_code == 200
        data = response.json()
        values = [c["value"] for c in data]
        assert "sales" in values
        assert "quality" in values
    
    def test_get_units(self, client):
        """Test getting KPI units."""
        response = client.get("/api/v1/kpi/units")
        
        assert response.status_code == 200
        data = response.json()
        values = [u["value"] for u in data]
        assert "percentage" in values
        assert "days" in values
        assert "ppm" in values
    
    def test_get_directions(self, client):
        """Test getting KPI directions."""
        response = client.get("/api/v1/kpi/directions")
        
        assert response.status_code == 200
        data = response.json()
        values = [d["value"] for d in data]
        assert "higher_is_better" in values
        assert "lower_is_better" in values
    
    def test_get_statuses(self, client):
        """Test getting KPI statuses."""
        response = client.get("/api/v1/kpi/statuses")
        
        assert response.status_code == 200
        data = response.json()
        values = [s["value"] for s in data]
        assert "green" in values
        assert "critical" in values
    
    def test_get_aggregation_types(self, client):
        """Test getting aggregation types."""
        response = client.get("/api/v1/kpi/aggregation-types")
        
        assert response.status_code == 200
        data = response.json()
        values = [a["value"] for a in data]
        assert "sum" in values
        assert "average" in values
    
    def test_get_trend_directions(self, client):
        """Test getting trend directions."""
        response = client.get("/api/v1/kpi/trend-directions")
        
        assert response.status_code == 200
        data = response.json()
        values = [t["value"] for t in data]
        assert "improving" in values
        assert "declining" in values


# --------------------------------------------------------------------------
# Integration Tests
# --------------------------------------------------------------------------

class TestIntegration:
    """Integration tests for complete workflows."""
    
    def test_complete_kpi_workflow(self, client):
        """Test complete KPI workflow."""
        # 1. Create custom KPI
        create_response = client.post(
            "/api/v1/kpi/definitions",
            json={
                "id": "workflow-kpi",
                "name": "Workflow Test KPI",
                "description": "Testing workflow",
                "category": "custom",
                "unit": "percentage",
                "direction": "higher_is_better",
                "threshold": {
                    "target": 90.0,
                    "warning_threshold": 10.0,
                    "critical_threshold": 20.0,
                },
            },
        )
        assert create_response.status_code == 201
        
        # 2. Record values
        for val in [85.0, 88.0, 90.0, 92.0, 95.0]:
            record_response = client.post(
                "/api/v1/kpi/values",
                json={"kpi_id": "workflow-kpi", "value": val},
            )
            assert record_response.status_code == 201
        
        # 3. Get latest value
        latest_response = client.get("/api/v1/kpi/values/workflow-kpi/latest")
        assert latest_response.status_code == 200
        assert latest_response.json()["value"] == 95.0
        
        # 4. Calculate KPI - without data_source or custom_calculator, this fails
        # Production KPIs must have proper data sources configured
        today = date.today().isoformat()
        week_ago = (date.today() - timedelta(days=7)).isoformat()
        
        calc_response = client.post(
            "/api/v1/kpi/calculate",
            json={
                "kpi_id": "workflow-kpi",
                "start_date": week_ago,
                "end_date": today,
            },
        )
        assert calc_response.status_code == 200
        # Without data_source/formula/custom_calculator, calculation fails
        assert calc_response.json()["success"] is False
        assert calc_response.json()["error"] is not None
        
        # 5. Create dashboard
        dash_response = client.post(
            "/api/v1/kpi/dashboards",
            json={
                "id": "workflow-dashboard",
                "name": "Workflow Dashboard",
                "description": "Test",
                "kpi_ids": ["workflow-kpi"],
            },
        )
        assert dash_response.status_code == 201
        
        # 6. Get dashboard data
        data_response = client.get(
            f"/api/v1/kpi/dashboards/workflow-dashboard/data"
            f"?start_date={week_ago}&end_date={today}"
        )
        assert data_response.status_code == 200
        assert "workflow-kpi" in data_response.json()["kpis"]
    
    def test_default_dashboards_have_data(self, client):
        """Test that default dashboards return data."""
        today = date.today().isoformat()
        month_ago = (date.today() - timedelta(days=30)).isoformat()
        
        dashboards = ["quote-to-cash", "production", "quality", "training", "andon"]
        
        for dashboard_id in dashboards:
            response = client.get(
                f"/api/v1/kpi/dashboards/{dashboard_id}/data"
                f"?start_date={month_ago}&end_date={today}"
            )
            assert response.status_code == 200
            data = response.json()
            assert len(data["kpis"]) > 0


# --------------------------------------------------------------------------
# Muda-aware nudges
# --------------------------------------------------------------------------


class TestMudaNudges:
    """Tests for muda-aware contextual nudges endpoint."""

    def test_generate_nudges_no_data(self, client: TestClient):
        response = client.post(
            "/api/v1/kpi/muda-nudges",
            json={"recipient_id": "op_1"},
        )

        assert response.status_code == 200
        assert response.json() == []

    def test_generate_nudges_from_low_fpy(self, client: TestClient):
        # FPY 94% => defect_rate_pct 6% => HIGH_DEFECT_RATE
        r1 = client.post(
            "/api/v1/kpi/values",
            json={
                "kpi_id": "first-pass-yield",
                "value": 94.0,
            },
        )
        assert r1.status_code == 201

        response = client.post(
            "/api/v1/kpi/muda-nudges",
            json={
                "recipient_id": "op_1",
                "include_knowledge": True,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["trigger"] == "high_defect_rate"
        assert data[0]["lesson_id"] is not None
        assert "Poka-Yoke" in (data[0]["lesson_title"] or "")
        assert isinstance(data[0]["recommended_documents"], list)

    def test_generate_multiple_nudges(self, client: TestClient):
        r1 = client.post(
            "/api/v1/kpi/values",
            json={"kpi_id": "first-pass-yield", "value": 94.0},
        )
        assert r1.status_code == 201

        r2 = client.post(
            "/api/v1/kpi/values",
            json={"kpi_id": "oee", "value": 50.0},
        )
        assert r2.status_code == 201

        response = client.post(
            "/api/v1/kpi/muda-nudges",
            json={"recipient_id": "op_1"},
        )
        assert response.status_code == 200
        data = response.json()
        triggers = [n["trigger"] for n in data]
        assert "high_defect_rate" in triggers
        assert "low_oee" in triggers
