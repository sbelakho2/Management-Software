"""
Tests for Stale Detection API endpoints.
"""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from sensei.api.v1.endpoints.stale_detection import (
    router,
    get_all_thresholds,
    get_thresholds_for_entity_type,
    detect_stale_opportunities,
    detect_stale_rfqs,
    detect_stale_tasks,
    run_full_scan,
    get_severity_levels,
    get_stale_reasons,
    get_entity_types,
    StaleDetectionRequest,
    FullScanRequest,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def reference_time():
    """Fixed reference time for testing."""
    return datetime(2025, 1, 15, 12, 0, 0)


@pytest.fixture
def sample_opportunities(reference_time):
    """Sample opportunity data for testing."""
    return [
        {
            "id": str(uuid4()),
            "name": "Stale Opportunity",
            "stage": "prospecting",
            "updated_at": (reference_time - timedelta(days=10)).isoformat(),
            "owner_id": str(uuid4()),
            "owner_name": "John Sales",
            "account_name": "Test Corp",
            "next_step": "Call customer",
            "next_step_date": (reference_time + timedelta(days=5)).isoformat(),
        },
        {
            "id": str(uuid4()),
            "name": "Fresh Opportunity",
            "stage": "qualification",
            "updated_at": (reference_time - timedelta(days=1)).isoformat(),
            "next_step": "Send proposal",
            "next_step_date": (reference_time + timedelta(days=3)).isoformat(),
        },
    ]


@pytest.fixture
def sample_rfqs(reference_time):
    """Sample RFQ data for testing."""
    return [
        {
            "id": str(uuid4()),
            "rfq_number": "RFQ-001",
            "status": "received",
            "updated_at": (reference_time - timedelta(days=5)).isoformat(),
        },
        {
            "id": str(uuid4()),
            "rfq_number": "RFQ-002",
            "status": "qualifying",
            "updated_at": (reference_time - timedelta(days=1)).isoformat(),
        },
    ]


@pytest.fixture
def sample_tasks(reference_time):
    """Sample task data for testing."""
    return [
        {
            "id": str(uuid4()),
            "title": "Stale Task",
            "status": "todo",
            "updated_at": (reference_time - timedelta(days=10)).isoformat(),
        },
        {
            "id": str(uuid4()),
            "title": "Fresh Task",
            "status": "in_progress",
            "updated_at": (reference_time - timedelta(days=1)).isoformat(),
        },
    ]


# =============================================================================
# Threshold Endpoint Tests
# =============================================================================


class TestStaleDetectionThresholdEndpoints:
    """Tests for threshold-related endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_all_thresholds(self):
        """Test getting all thresholds for all entity types."""
        result = await get_all_thresholds()
        
        assert "opportunity" in result
        assert "rfq" in result
        assert "task" in result
        
        # Check opportunity thresholds
        assert "default" in result["opportunity"]
        assert "prospecting" in result["opportunity"]
        assert result["opportunity"]["prospecting"].days_until_stale == 5
    
    @pytest.mark.asyncio
    async def test_get_opportunity_thresholds(self):
        """Test getting thresholds for opportunities."""
        result = await get_thresholds_for_entity_type("opportunity")
        
        assert "default" in result
        assert "prospecting" in result
        assert "qualification" in result
        assert "proposal" in result
    
    @pytest.mark.asyncio
    async def test_get_rfq_thresholds(self):
        """Test getting thresholds for RFQs."""
        result = await get_thresholds_for_entity_type("rfq")
        
        assert "default" in result
        assert "received" in result
        assert result["received"].days_until_stale == 2
    
    @pytest.mark.asyncio
    async def test_get_task_thresholds(self):
        """Test getting thresholds for tasks."""
        result = await get_thresholds_for_entity_type("task")
        
        assert "default" in result
        assert "blocked" in result
        assert result["blocked"].days_until_stale == 2
    
    @pytest.mark.asyncio
    async def test_get_invalid_entity_type_thresholds(self):
        """Test getting thresholds for invalid entity type."""
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            await get_thresholds_for_entity_type("invalid")
        
        assert exc_info.value.status_code == 400
        assert "Invalid entity type" in exc_info.value.detail


# =============================================================================
# Detection Endpoint Tests
# =============================================================================


class TestStaleDetectionEndpoints:
    """Tests for detection endpoints."""
    
    @pytest.mark.asyncio
    async def test_detect_stale_opportunities(self, sample_opportunities, reference_time):
        """Test detecting stale opportunities."""
        request = StaleDetectionRequest(
            entities=sample_opportunities,
            reference_time=reference_time,
        )
        
        result = await detect_stale_opportunities(request)
        
        assert result.entity_type == "opportunity"
        assert result.total_scanned == 2
        assert result.stale_count >= 1  # At least one stale
        assert len(result.stale_entities) >= 1
        
        # Check stale entity structure
        stale = result.stale_entities[0]
        assert stale.entity_id is not None
        assert stale.entity_name is not None
        assert stale.reason is not None
        assert stale.severity is not None
        assert stale.suggested_action is not None
    
    @pytest.mark.asyncio
    async def test_detect_stale_rfqs(self, sample_rfqs, reference_time):
        """Test detecting stale RFQs."""
        request = StaleDetectionRequest(
            entities=sample_rfqs,
            reference_time=reference_time,
        )
        
        result = await detect_stale_rfqs(request)
        
        assert result.entity_type == "rfq"
        assert result.total_scanned == 2
        assert result.stale_count >= 1
    
    @pytest.mark.asyncio
    async def test_detect_stale_tasks(self, sample_tasks, reference_time):
        """Test detecting stale tasks."""
        request = StaleDetectionRequest(
            entities=sample_tasks,
            reference_time=reference_time,
        )
        
        result = await detect_stale_tasks(request)
        
        assert result.entity_type == "task"
        assert result.total_scanned == 2
        assert result.stale_count >= 1
    
    @pytest.mark.asyncio
    async def test_detect_with_default_reference_time(self):
        """Test detection uses current time when not specified."""
        # Create an entity that's very old (will be stale regardless of reference time)
        entities = [
            {
                "id": str(uuid4()),
                "name": "Very Old Opportunity",
                "stage": "prospecting",
                "updated_at": (datetime.now() - timedelta(days=100)).isoformat(),
                "next_step": "Call",
                "next_step_date": (datetime.now() + timedelta(days=5)).isoformat(),
            }
        ]
        
        request = StaleDetectionRequest(entities=entities)  # No reference_time
        result = await detect_stale_opportunities(request)
        
        assert result.stale_count == 1
    
    @pytest.mark.asyncio
    async def test_detect_empty_entities(self):
        """Test detection with empty entity list."""
        request = StaleDetectionRequest(entities=[])
        result = await detect_stale_opportunities(request)
        
        assert result.total_scanned == 0
        assert result.stale_count == 0
        assert result.stale_entities == []


# =============================================================================
# Full Scan Endpoint Tests
# =============================================================================


class TestFullScanEndpoint:
    """Tests for full scan endpoint."""
    
    @pytest.mark.asyncio
    async def test_full_scan(self, sample_opportunities, sample_rfqs, sample_tasks, reference_time):
        """Test running a full scan across all entity types."""
        request = FullScanRequest(
            opportunities=sample_opportunities,
            rfqs=sample_rfqs,
            tasks=sample_tasks,
            reference_time=reference_time,
        )
        
        result = await run_full_scan(request)
        
        assert result.total_scanned is not None
        assert result.total_stale is not None
        assert result.total_critical is not None
        assert result.total_high is not None
        assert result.by_entity_type is not None
        assert result.requires_immediate_attention is not None
        
        # Should have scanned all entities
        assert result.total_scanned == 6  # 2 + 2 + 2
        
        # Should have breakdown by entity type
        assert "opportunity" in result.by_entity_type
        assert "rfq" in result.by_entity_type
        assert "task" in result.by_entity_type
    
    @pytest.mark.asyncio
    async def test_full_scan_empty(self):
        """Test full scan with empty data."""
        request = FullScanRequest()
        result = await run_full_scan(request)
        
        assert result.total_scanned == 0
        assert result.total_stale == 0


# =============================================================================
# Reference Data Endpoints Tests
# =============================================================================


class TestReferenceDataEndpoints:
    """Tests for reference data endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_severity_levels(self):
        """Test getting severity level definitions."""
        result = await get_severity_levels()
        
        assert len(result) == 4
        values = [s["value"] for s in result]
        assert "low" in values
        assert "medium" in values
        assert "high" in values
        assert "critical" in values
    
    @pytest.mark.asyncio
    async def test_get_stale_reasons(self):
        """Test getting stale reason definitions."""
        result = await get_stale_reasons()
        
        assert len(result) == 6
        values = [r["value"] for r in result]
        assert "no_activity" in values
        assert "stuck_in_status" in values
        assert "overdue" in values
        assert "no_next_step" in values
        assert "next_step_overdue" in values
        assert "waiting_too_long" in values
    
    @pytest.mark.asyncio
    async def test_get_entity_types(self):
        """Test getting supported entity types."""
        result = await get_entity_types()
        
        assert len(result) == 3
        values = [e["value"] for e in result]
        assert "opportunity" in values
        assert "rfq" in values
        assert "task" in values


# =============================================================================
# Response Structure Tests
# =============================================================================


class TestResponseStructure:
    """Tests for response structure validation."""
    
    @pytest.mark.asyncio
    async def test_stale_entity_response_structure(self, reference_time):
        """Test that stale entity response has all required fields."""
        entities = [
            {
                "id": str(uuid4()),
                "name": "Test Opportunity",
                "stage": "prospecting",
                "updated_at": (reference_time - timedelta(days=20)).isoformat(),
                "owner_id": str(uuid4()),
                "owner_name": "Test User",
                "account_name": "Test Account",
                "next_step": "Call",
                "next_step_date": (reference_time + timedelta(days=5)).isoformat(),
                "opportunity_number": "OPP-001",
                "amount": 50000,
                "probability": 50,
            }
        ]
        
        request = StaleDetectionRequest(
            entities=entities,
            reference_time=reference_time,
        )
        result = await detect_stale_opportunities(request)
        
        assert len(result.stale_entities) == 1
        stale = result.stale_entities[0]
        
        # Check all fields are present
        assert stale.entity_id is not None
        assert stale.entity_type is not None
        assert stale.entity_name is not None
        assert stale.reason is not None
        assert stale.severity is not None
        assert stale.days_stale is not None
        assert stale.last_activity_at is not None
        assert stale.status is not None
        assert stale.suggested_action is not None
        assert stale.metadata is not None
        
        # Check values
        assert stale.entity_name == "Test Opportunity"
        assert stale.owner_name == "Test User"
        assert stale.account_name == "Test Account"
    
    @pytest.mark.asyncio
    async def test_thresholds_in_detection_response(self, sample_opportunities, reference_time):
        """Test that detection response includes thresholds used."""
        request = StaleDetectionRequest(
            entities=sample_opportunities,
            reference_time=reference_time,
        )
        result = await detect_stale_opportunities(request)
        
        assert result.thresholds_used is not None
        assert "default" in result.thresholds_used
        assert "prospecting" in result.thresholds_used
        
        # Check threshold structure
        threshold = result.thresholds_used["prospecting"]
        assert "days" in threshold
        assert "reason" in threshold
