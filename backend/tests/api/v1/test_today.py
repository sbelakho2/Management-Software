"""
Comprehensive tests for the Today Screen (Manager GPS) API endpoints.

Tests cover all API endpoints for the Today Screen dashboard:
- Priority management
- Risk tracking
- Commitment management
- Abnormality tracking
- Micro-drill questions
- LSW summary
- Quick metrics
- Full dashboard data
- Metadata endpoints
"""

import pytest
from datetime import date, timedelta
from uuid import uuid4

from fastapi import status
from fastapi.testclient import TestClient

from sensei.main import app
from sensei.services.today_screen import (
    RiskCategory,
    AbnormalityType,
    CommitmentType,
    PriorityLevel,
    LSWChecklistStatus,
    reset_today_screen_service,
)


@pytest.fixture
def client():
    """Provide a test client with fresh service."""
    reset_today_screen_service()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def sample_user_id():
    """Provide a sample user ID."""
    return str(uuid4())


# ============================================================================
# Priority Endpoints Tests
# ============================================================================


class TestPriorityEndpoints:
    """Tests for priority management endpoints."""

    def test_get_user_priorities_empty(self, client, sample_user_id):
        """Test getting priorities for user with none."""
        response = client.get(f"/api/v1/today/priorities/{sample_user_id}")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    def test_add_priority(self, client, sample_user_id):
        """Test adding a priority."""
        data = {
            "entity_type": "quote",
            "entity_id": str(uuid4()),
            "title": "Urgent quote",
            "priority_level": "high",
            "description": "Needs immediate attention",
        }
        response = client.post(f"/api/v1/today/priorities/{sample_user_id}", json=data)
        
        assert response.status_code == status.HTTP_201_CREATED
        result = response.json()
        assert result["title"] == "Urgent quote"
        assert result["priority_level"] == "high"
        assert result["is_user_selected"] is False

    def test_get_user_priorities_after_add(self, client, sample_user_id):
        """Test getting priorities after adding."""
        # Add a priority
        data = {
            "entity_type": "quote",
            "entity_id": str(uuid4()),
            "title": "Test priority",
            "priority_level": "medium",
        }
        client.post(f"/api/v1/today/priorities/{sample_user_id}", json=data)

        # Get priorities
        response = client.get(f"/api/v1/today/priorities/{sample_user_id}")
        
        assert response.status_code == status.HTTP_200_OK
        priorities = response.json()
        assert len(priorities) == 1
        assert priorities[0]["title"] == "Test priority"

    def test_set_top_priorities(self, client, sample_user_id):
        """Test setting top 3 priorities."""
        # Add priorities
        priority_ids = []
        for i in range(5):
            data = {
                "entity_type": "quote",
                "entity_id": str(uuid4()),
                "title": f"Priority {i+1}",
                "priority_level": "medium",
            }
            response = client.post(f"/api/v1/today/priorities/{sample_user_id}", json=data)
            priority_ids.append(response.json()["id"])

        # Set top 3
        response = client.post(
            f"/api/v1/today/priorities/{sample_user_id}/top",
            json={"priority_ids": priority_ids[:3]},
        )
        
        assert response.status_code == status.HTTP_200_OK
        selected = response.json()
        assert len(selected) == 3
        for i, p in enumerate(selected):
            assert p["is_user_selected"] is True
            assert p["rank"] == i + 1

    def test_set_top_priorities_max_three(self, client, sample_user_id):
        """Test that setting more than 3 priorities fails."""
        priority_ids = [str(uuid4()) for _ in range(4)]
        
        response = client.post(
            f"/api/v1/today/priorities/{sample_user_id}/top",
            json={"priority_ids": priority_ids},
        )
        
        # Schema validation (max_length=3) rejects this
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_remove_priority(self, client, sample_user_id):
        """Test removing a priority."""
        # Add priority
        data = {
            "entity_type": "quote",
            "entity_id": str(uuid4()),
            "title": "To be removed",
            "priority_level": "low",
        }
        response = client.post(f"/api/v1/today/priorities/{sample_user_id}", json=data)
        priority_id = response.json()["id"]

        # Remove it
        response = client.delete(
            f"/api/v1/today/priorities/{sample_user_id}/{priority_id}"
        )
        
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify it's gone
        response = client.get(f"/api/v1/today/priorities/{sample_user_id}")
        assert len(response.json()) == 0

    def test_remove_nonexistent_priority(self, client, sample_user_id):
        """Test removing a non-existent priority."""
        response = client.delete(
            f"/api/v1/today/priorities/{sample_user_id}/{uuid4()}"
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_priorities_filtered(self, client, sample_user_id):
        """Test getting priorities with filters."""
        # Add priorities and select some
        priority_ids = []
        for i in range(4):
            data = {
                "entity_type": "quote",
                "entity_id": str(uuid4()),
                "title": f"Priority {i+1}",
                "priority_level": "medium",
            }
            response = client.post(f"/api/v1/today/priorities/{sample_user_id}", json=data)
            priority_ids.append(response.json()["id"])

        client.post(
            f"/api/v1/today/priorities/{sample_user_id}/top",
            json={"priority_ids": priority_ids[:2]},
        )

        # Get only selected
        response = client.get(
            f"/api/v1/today/priorities/{sample_user_id}",
            params={"include_selected": True, "include_unselected": False},
        )
        assert len(response.json()) == 2

        # Get only unselected
        response = client.get(
            f"/api/v1/today/priorities/{sample_user_id}",
            params={"include_selected": False, "include_unselected": True},
        )
        assert len(response.json()) == 2


# ============================================================================
# Risk Endpoints Tests
# ============================================================================


class TestRiskEndpoints:
    """Tests for risk management endpoints."""

    def test_add_risk(self, client):
        """Test adding a risk."""
        data = {
            "title": "Delivery delay",
            "category": "delivery",
            "severity": 7,
            "probability": 5,
            "description": "Vendor issue",
            "mitigation": "Find backup supplier",
        }
        response = client.post("/api/v1/today/risks", json=data)
        
        assert response.status_code == status.HTTP_201_CREATED
        result = response.json()
        assert result["title"] == "Delivery delay"
        assert result["category"] == "delivery"
        assert result["risk_score"] == 35

    def test_get_risks(self, client):
        """Test getting all risks."""
        # Add a risk
        data = {
            "title": "Test risk",
            "category": "quality",
            "severity": 5,
            "probability": 5,
        }
        client.post("/api/v1/today/risks", json=data)

        response = client.get("/api/v1/today/risks")
        
        assert response.status_code == status.HTTP_200_OK
        risks = response.json()
        assert len(risks) >= 1

    def test_get_risks_by_category(self, client):
        """Test getting risks filtered by category."""
        # Add risks
        client.post("/api/v1/today/risks", json={
            "title": "Delivery 1", "category": "delivery", "severity": 5, "probability": 5,
        })
        client.post("/api/v1/today/risks", json={
            "title": "Quality 1", "category": "quality", "severity": 4, "probability": 4,
        })

        response = client.get("/api/v1/today/risks", params={"category": "delivery"})
        
        assert response.status_code == status.HTTP_200_OK
        risks = response.json()
        assert all(r["category"] == "delivery" for r in risks)

    def test_get_risks_by_category_grouped(self, client):
        """Test getting risks grouped by category."""
        # Add risks
        client.post("/api/v1/today/risks", json={
            "title": "Delivery 1", "category": "delivery", "severity": 5, "probability": 5,
        })
        client.post("/api/v1/today/risks", json={
            "title": "Quality 1", "category": "quality", "severity": 4, "probability": 4,
        })

        response = client.get("/api/v1/today/risks/by-category")
        
        assert response.status_code == status.HTTP_200_OK
        grouped = response.json()
        assert isinstance(grouped, list)
        
        categories = [g["category"] for g in grouped]
        assert "delivery" in categories
        assert "quality" in categories

    def test_get_top_risks(self, client):
        """Test getting top N risks."""
        # Add several risks with different scores
        for i, (sev, prob) in enumerate([(8, 7), (3, 3), (5, 5), (9, 8)]):
            client.post("/api/v1/today/risks", json={
                "title": f"Risk {i+1}",
                "category": "delivery",
                "severity": sev,
                "probability": prob,
            })

        response = client.get("/api/v1/today/risks/top", params={"top_n": 2})
        
        assert response.status_code == status.HTTP_200_OK
        risks = response.json()
        assert len(risks) == 2
        # Should be sorted by risk score descending
        assert risks[0]["risk_score"] >= risks[1]["risk_score"]


# ============================================================================
# Commitment Endpoints Tests
# ============================================================================


class TestCommitmentEndpoints:
    """Tests for commitment management endpoints."""

    def test_add_commitment(self, client):
        """Test adding a commitment."""
        data = {
            "title": "Quote deadline",
            "commitment_type": "quote_due",
            "due_date": str(date.today() + timedelta(days=1)),
            "description": "Customer expects response",
        }
        response = client.post("/api/v1/today/commitments", json=data)
        
        assert response.status_code == status.HTTP_201_CREATED
        result = response.json()
        assert result["title"] == "Quote deadline"
        assert result["commitment_type"] == "quote_due"
        assert result["is_completed"] is False

    def test_get_commitments(self, client):
        """Test getting commitments."""
        # Add a commitment
        client.post("/api/v1/today/commitments", json={
            "title": "Test commitment",
            "commitment_type": "task_due",
            "due_date": str(date.today() + timedelta(days=1)),
        })

        response = client.get("/api/v1/today/commitments")
        
        assert response.status_code == status.HTTP_200_OK
        commitments = response.json()
        assert len(commitments) >= 1

    def test_complete_commitment(self, client):
        """Test completing a commitment."""
        # Add a commitment
        response = client.post("/api/v1/today/commitments", json={
            "title": "To be completed",
            "commitment_type": "meeting",
            "due_date": str(date.today()),
        })
        commitment_id = response.json()["id"]

        # Complete it
        response = client.post(f"/api/v1/today/commitments/{commitment_id}/complete")
        
        assert response.status_code == status.HTTP_200_OK
        result = response.json()
        assert result["is_completed"] is True

    def test_complete_nonexistent_commitment(self, client):
        """Test completing a non-existent commitment."""
        response = client.post(f"/api/v1/today/commitments/{uuid4()}/complete")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_commitments_by_date(self, client, sample_user_id):
        """Test getting commitments for a specific date."""
        today = date.today()
        tomorrow = today + timedelta(days=1)

        # Add commitments for different dates
        client.post("/api/v1/today/commitments", json={
            "title": "Today's",
            "commitment_type": "task_due",
            "due_date": str(today),
            "owner_id": sample_user_id,
        })
        client.post("/api/v1/today/commitments", json={
            "title": "Tomorrow's",
            "commitment_type": "task_due",
            "due_date": str(tomorrow),
            "owner_id": sample_user_id,
        })

        response = client.get(
            "/api/v1/today/commitments",
            params={"user_id": sample_user_id, "target_date": str(today)},
        )
        
        assert response.status_code == status.HTTP_200_OK
        commitments = response.json()
        assert all(c["due_date"] == str(today) for c in commitments)


# ============================================================================
# Abnormality Endpoints Tests
# ============================================================================


class TestAbnormalityEndpoints:
    """Tests for abnormality management endpoints."""

    def test_add_abnormality(self, client):
        """Test adding an abnormality."""
        data = {
            "title": "Quote overdue",
            "abnormality_type": "late_quote",
            "entity_type": "quote",
            "entity_id": str(uuid4()),
            "days_stale": 5,
            "suggested_action": "Escalate to manager",
        }
        response = client.post("/api/v1/today/abnormalities", json=data)
        
        assert response.status_code == status.HTTP_201_CREATED
        result = response.json()
        assert result["title"] == "Quote overdue"
        assert result["abnormality_type"] == "late_quote"
        assert result["days_stale"] == 5

    def test_get_abnormalities(self, client):
        """Test getting abnormalities."""
        # Add an abnormality
        client.post("/api/v1/today/abnormalities", json={
            "title": "Test abnormality",
            "abnormality_type": "stalled_rfq",
            "entity_type": "rfq",
            "entity_id": str(uuid4()),
            "days_stale": 3,
        })

        response = client.get("/api/v1/today/abnormalities")
        
        assert response.status_code == status.HTTP_200_OK
        abnormalities = response.json()
        assert len(abnormalities) >= 1

    def test_get_abnormalities_by_type(self, client):
        """Test filtering abnormalities by type."""
        # Add abnormalities of different types
        client.post("/api/v1/today/abnormalities", json={
            "title": "Late 1", "abnormality_type": "late_quote",
            "entity_type": "quote", "entity_id": str(uuid4()), "days_stale": 1,
        })
        client.post("/api/v1/today/abnormalities", json={
            "title": "Stalled 1", "abnormality_type": "stalled_rfq",
            "entity_type": "rfq", "entity_id": str(uuid4()), "days_stale": 2,
        })

        response = client.get(
            "/api/v1/today/abnormalities",
            params={"abnormality_type": "late_quote"},
        )
        
        assert response.status_code == status.HTTP_200_OK
        abnormalities = response.json()
        assert all(a["abnormality_type"] == "late_quote" for a in abnormalities)

    def test_get_abnormality_counts(self, client):
        """Test getting abnormality counts by type."""
        # Add abnormalities
        for _ in range(2):
            client.post("/api/v1/today/abnormalities", json={
                "title": "Late", "abnormality_type": "late_quote",
                "entity_type": "quote", "entity_id": str(uuid4()), "days_stale": 1,
            })
        client.post("/api/v1/today/abnormalities", json={
            "title": "Stalled", "abnormality_type": "stalled_rfq",
            "entity_type": "rfq", "entity_id": str(uuid4()), "days_stale": 2,
        })

        response = client.get("/api/v1/today/abnormalities/counts")
        
        assert response.status_code == status.HTTP_200_OK
        counts = response.json()
        assert counts.get("late_quote", 0) >= 2
        assert counts.get("stalled_rfq", 0) >= 1

    def test_resolve_abnormality(self, client):
        """Test resolving an abnormality."""
        # Add an abnormality
        response = client.post("/api/v1/today/abnormalities", json={
            "title": "To be resolved",
            "abnormality_type": "missing_ctq",
            "entity_type": "quote",
            "entity_id": str(uuid4()),
            "days_stale": 1,
        })
        abnormality_id = response.json()["id"]

        # Resolve it
        response = client.delete(f"/api/v1/today/abnormalities/{abnormality_id}")
        
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_resolve_nonexistent_abnormality(self, client):
        """Test resolving a non-existent abnormality."""
        response = client.delete(f"/api/v1/today/abnormalities/{uuid4()}")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ============================================================================
# Micro-Drill Endpoints Tests
# ============================================================================


class TestMicroDrillEndpoints:
    """Tests for micro-drill endpoints."""

    def test_add_micro_drill(self, client):
        """Test adding a micro-drill."""
        data = {
            "question": "What is standard lead time?",
            "answer": "4-6 weeks",
            "category": "operations",
            "difficulty": 2,
            "hint": "Think about the process",
        }
        response = client.post("/api/v1/today/drills", json=data)
        
        assert response.status_code == status.HTTP_201_CREATED
        result = response.json()
        assert result["question"] == "What is standard lead time?"
        assert result["difficulty"] == 2

    def test_get_todays_drills(self, client, sample_user_id):
        """Test getting today's drills."""
        # Add some drills
        for i in range(5):
            client.post("/api/v1/today/drills", json={
                "question": f"Question {i+1}",
                "answer": f"Answer {i+1}",
                "category": "test",
                "difficulty": 2,
            })

        response = client.get(f"/api/v1/today/drills/{sample_user_id}")
        
        assert response.status_code == status.HTTP_200_OK
        drills = response.json()
        # Default count is 3
        assert len(drills) <= 3

    def test_get_todays_drills_custom_count(self, client, sample_user_id):
        """Test getting custom number of drills."""
        # Add some drills
        for i in range(10):
            client.post("/api/v1/today/drills", json={
                "question": f"Question {i+1}",
                "answer": f"Answer {i+1}",
                "category": "test",
                "difficulty": 2,
            })

        response = client.get(
            f"/api/v1/today/drills/{sample_user_id}",
            params={"count": 5},
        )
        
        assert response.status_code == status.HTTP_200_OK
        drills = response.json()
        assert len(drills) <= 5

    def test_complete_drill(self, client, sample_user_id):
        """Test completing a drill."""
        # Add a drill
        response = client.post("/api/v1/today/drills", json={
            "question": "Test",
            "answer": "Answer",
            "category": "test",
            "difficulty": 1,
        })
        drill_id = response.json()["id"]

        # Complete it
        response = client.post(
            f"/api/v1/today/drills/{sample_user_id}/{drill_id}/complete",
            json={"correct": True},
        )
        
        assert response.status_code == status.HTTP_200_OK
        result = response.json()
        assert result["streak"] >= 1
        assert result["total_completed"] >= 1
        assert "accuracy" in result

    def test_get_drill_progress(self, client, sample_user_id):
        """Test getting drill progress."""
        # Complete a drill
        response = client.post("/api/v1/today/drills", json={
            "question": "Test",
            "answer": "Answer",
            "category": "test",
            "difficulty": 1,
        })
        drill_id = response.json()["id"]
        client.post(
            f"/api/v1/today/drills/{sample_user_id}/{drill_id}/complete",
            json={"correct": True},
        )

        # Get progress
        response = client.get(f"/api/v1/today/drills/{sample_user_id}/progress")
        
        assert response.status_code == status.HTTP_200_OK
        progress = response.json()
        assert progress["drills_completed_today"] >= 1
        assert "streak" in progress
        assert "accuracy" in progress


# ============================================================================
# LSW Summary Endpoint Tests
# ============================================================================


class TestLSWSummaryEndpoints:
    """Tests for LSW summary endpoint."""

    def test_get_lsw_summary(self, client, sample_user_id):
        """Test getting LSW checklist summary."""
        response = client.get(f"/api/v1/today/lsw/{sample_user_id}")
        
        assert response.status_code == status.HTTP_200_OK
        summary = response.json()
        
        # Check daily fields
        assert summary["daily_status"] in [s.value for s in LSWChecklistStatus]
        assert summary["daily_total"] >= 0
        assert summary["daily_completed"] >= 0
        
        # Check weekly fields
        assert summary["weekly_status"] in [s.value for s in LSWChecklistStatus]
        assert summary["weekly_total"] >= 0
        
        # Check monthly fields
        assert summary["monthly_status"] in [s.value for s in LSWChecklistStatus]
        
        # Check other fields
        assert summary["overdue_count"] >= 0


# ============================================================================
# Quick Metrics Endpoint Tests
# ============================================================================


class TestQuickMetricsEndpoints:
    """Tests for quick metrics endpoint."""

    def test_get_quick_metrics(self, client, sample_user_id):
        """Test getting quick metrics."""
        response = client.get(f"/api/v1/today/metrics/{sample_user_id}")
        
        assert response.status_code == status.HTTP_200_OK
        metrics = response.json()
        
        assert isinstance(metrics, list)
        assert len(metrics) > 0
        
        for metric in metrics:
            assert "id" in metric
            assert "name" in metric
            assert "value" in metric
            assert metric["trend"] in ["up", "down", "stable"]
            assert metric["status"] in ["good", "warning", "critical"]


# ============================================================================
# Full Today Screen Endpoint Tests
# ============================================================================


class TestTodayScreenEndpoints:
    """Tests for full today screen endpoint."""

    def test_get_today_screen(self, client, sample_user_id):
        """Test getting complete today screen data."""
        response = client.get(
            f"/api/v1/today/screen/{sample_user_id}",
            params={"user_name": "John Doe"},
        )
        
        assert response.status_code == status.HTTP_200_OK
        screen = response.json()
        
        # Check user info
        assert screen["user_id"] == sample_user_id
        assert screen["user_name"] == "John Doe"
        assert "greeting" in screen
        assert "John" in screen["greeting"]
        
        # Check priorities
        assert "top_priorities" in screen
        assert "unselected_priorities" in screen
        
        # Check risks
        assert "top_risks" in screen
        assert "total_risk_count" in screen
        assert "critical_risk_count" in screen
        
        # Check commitments
        assert "todays_commitments" in screen
        assert "tomorrows_commitments" in screen
        assert "overdue_commitments" in screen
        
        # Check abnormalities
        assert "abnormalities" in screen
        assert "abnormality_counts" in screen
        
        # Check drills
        assert "todays_micro_drills" in screen
        assert "drills_completed_today" in screen
        assert "drill_streak" in screen
        
        # Check LSW summary
        assert "lsw_summary" in screen
        
        # Check metrics
        assert "quick_metrics" in screen
        
        # Check timestamps
        assert "generated_at" in screen
        assert "cache_valid_until" in screen

    def test_get_today_screen_with_data(self, client, sample_user_id):
        """Test getting today screen with populated data."""
        # Add some data
        priority_ids = []
        for i in range(3):
            response = client.post(
                f"/api/v1/today/priorities/{sample_user_id}",
                json={
                    "entity_type": "quote",
                    "entity_id": str(uuid4()),
                    "title": f"Priority {i+1}",
                    "priority_level": "high",
                },
            )
            priority_ids.append(response.json()["id"])
        
        # Select top priorities
        client.post(
            f"/api/v1/today/priorities/{sample_user_id}/top",
            json={"priority_ids": priority_ids},
        )

        # Add risk
        client.post("/api/v1/today/risks", json={
            "title": "Test risk",
            "category": "delivery",
            "severity": 7,
            "probability": 5,
        })

        # Add commitment for today
        client.post("/api/v1/today/commitments", json={
            "title": "Today's task",
            "commitment_type": "task_due",
            "due_date": str(date.today()),
            "owner_id": sample_user_id,
        })

        # Get screen
        response = client.get(
            f"/api/v1/today/screen/{sample_user_id}",
            params={"user_name": "Jane Smith"},
        )
        
        assert response.status_code == status.HTTP_200_OK
        screen = response.json()
        
        assert len(screen["top_priorities"]) == 3
        assert screen["total_risk_count"] >= 1
        assert len(screen["todays_commitments"]) >= 1

    def test_get_today_screen_missing_user_name(self, client, sample_user_id):
        """Test getting today screen without user_name fails."""
        response = client.get(f"/api/v1/today/screen/{sample_user_id}")
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ============================================================================
# Metadata Endpoints Tests
# ============================================================================


class TestMetadataEndpoints:
    """Tests for metadata endpoints."""

    def test_get_risk_categories(self, client):
        """Test getting risk categories."""
        response = client.get("/api/v1/today/meta/risk-categories")
        
        assert response.status_code == status.HTTP_200_OK
        categories = response.json()
        
        assert isinstance(categories, list)
        assert "delivery" in categories
        assert "quality" in categories
        assert "cash" in categories
        assert "reputation" in categories

    def test_get_abnormality_types(self, client):
        """Test getting abnormality types."""
        response = client.get("/api/v1/today/meta/abnormality-types")
        
        assert response.status_code == status.HTTP_200_OK
        types = response.json()
        
        assert isinstance(types, list)
        assert "late_quote" in types
        assert "stalled_rfq" in types
        assert "missing_ctq" in types

    def test_get_commitment_types(self, client):
        """Test getting commitment types."""
        response = client.get("/api/v1/today/meta/commitment-types")
        
        assert response.status_code == status.HTTP_200_OK
        types = response.json()
        
        assert isinstance(types, list)
        assert "quote_due" in types
        assert "meeting" in types
        assert "follow_up" in types

    def test_get_priority_levels(self, client):
        """Test getting priority levels."""
        response = client.get("/api/v1/today/meta/priority-levels")
        
        assert response.status_code == status.HTTP_200_OK
        levels = response.json()
        
        assert isinstance(levels, list)
        assert "high" in levels
        assert "medium" in levels
        assert "low" in levels

    def test_get_lsw_statuses(self, client):
        """Test getting LSW statuses."""
        response = client.get("/api/v1/today/meta/lsw-statuses")
        
        assert response.status_code == status.HTTP_200_OK
        statuses = response.json()
        
        assert isinstance(statuses, list)
        assert "not_started" in statuses
        assert "in_progress" in statuses
        assert "completed" in statuses
        assert "overdue" in statuses


# ============================================================================
# Edge Cases and Validation Tests
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and validation."""

    def test_priority_validation(self, client, sample_user_id):
        """Test priority validation."""
        # Empty title
        response = client.post(
            f"/api/v1/today/priorities/{sample_user_id}",
            json={
                "entity_type": "quote",
                "entity_id": str(uuid4()),
                "title": "",
                "priority_level": "medium",
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_risk_validation(self, client):
        """Test risk validation."""
        # Severity out of range (should still work due to clamping)
        response = client.post("/api/v1/today/risks", json={
            "title": "Test",
            "category": "delivery",
            "severity": 15,  # Out of range
            "probability": 5,
        })
        # Should be rejected by Pydantic validation
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_commitment_validation(self, client):
        """Test commitment validation."""
        # Invalid due_time format
        response = client.post("/api/v1/today/commitments", json={
            "title": "Test",
            "commitment_type": "task_due",
            "due_date": str(date.today()),
            "due_time": "invalid",
        })
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_drill_validation(self, client):
        """Test drill validation."""
        # Difficulty out of range
        response = client.post("/api/v1/today/drills", json={
            "question": "Test",
            "answer": "Answer",
            "category": "test",
            "difficulty": 10,  # Out of range
        })
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_invalid_uuid_format(self, client):
        """Test invalid UUID format."""
        response = client.get("/api/v1/today/priorities/invalid-uuid")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_abnormality_validation(self, client):
        """Test abnormality validation."""
        # Missing required fields
        response = client.post("/api/v1/today/abnormalities", json={
            "title": "Test",
            # Missing abnormality_type, entity_type, entity_id
        })
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
