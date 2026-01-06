"""Tests for Risk API endpoints.

Tests cover:
- Risk CRUD operations
- Risk workflow transitions (analyze, mitigate, monitor, close, accept, occurred)
- Risk mitigations (add, update, complete, delete)
- Query endpoints
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from sensei.api.v1.endpoints.risk import (
    router,
    create_risk,
    get_risk,
    list_risks,
    update_risk,
    delete_risk,
    analyze_risk,
    start_mitigation,
    monitor_risk,
    close_risk,
    accept_risk,
    record_occurrence,
    record_review,
    add_mitigation,
    list_mitigations,
    get_mitigation,
    update_mitigation,
    complete_mitigation,
    delete_mitigation,
    get_risk_by_number,
    get_high_priority_risks,
    get_open_risks,
    RiskCreate,
    RiskUpdate,
    ResidualAssessmentData,
    OccurrenceData,
    MitigationCreate,
    MitigationUpdate,
)
from sensei.api.exceptions import ConflictError, NotFoundError
from sensei.models.risk import (
    Risk,
    RiskMitigation,
    RiskCategory,
    RiskStatus,
    RiskSeverity,
    RiskLikelihood,
    MitigationStatus,
)


# =============================================================================
# Test Fixtures and Helpers
# =============================================================================


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = AsyncMock()
    db.add = MagicMock()
    db.delete = AsyncMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    return db


@pytest.fixture
def mock_user():
    """Create a mock current user."""
    user = MagicMock()
    user.id = uuid4()
    return user


def make_result(
    scalar_one_or_none=None,
    scalars_all=None,
    scalar_one=None,
):
    """Create a mock result object."""
    result = MagicMock()
    if scalar_one_or_none is not None or scalar_one_or_none is None:
        result.scalar_one_or_none.return_value = scalar_one_or_none
    if scalars_all is not None:
        scalars_result = MagicMock()
        scalars_result.all.return_value = scalars_all
        result.scalars.return_value = scalars_result
    if scalar_one is not None:
        result.scalar_one.return_value = scalar_one
    return result


def create_mock_risk(
    risk_id=None,
    risk_number="RISK-0001",
    title="Test Risk",
    description="Test risk description",
    category=RiskCategory.TECHNICAL.value,
    status=RiskStatus.IDENTIFIED.value,
    inherent_likelihood=RiskLikelihood.POSSIBLE.value,
    inherent_severity=RiskSeverity.MODERATE.value,
    inherent_likelihood_score=3,
    inherent_severity_score=3,
    inherent_risk_score=9,
    **kwargs,
):
    """Create a mock Risk object."""
    risk = MagicMock(spec=Risk)
    risk.id = risk_id or uuid4()
    risk.risk_number = risk_number
    risk.title = title
    risk.description = description
    risk.category = category
    risk.status = status
    risk.related_entity_type = kwargs.get("related_entity_type")
    risk.related_entity_id = kwargs.get("related_entity_id")
    risk.rfq_id = kwargs.get("rfq_id")
    risk.inherent_likelihood = inherent_likelihood
    risk.inherent_severity = inherent_severity
    risk.inherent_likelihood_score = inherent_likelihood_score
    risk.inherent_severity_score = inherent_severity_score
    risk.inherent_risk_score = inherent_risk_score
    risk.residual_likelihood = kwargs.get("residual_likelihood")
    risk.residual_severity = kwargs.get("residual_severity")
    risk.residual_likelihood_score = kwargs.get("residual_likelihood_score")
    risk.residual_severity_score = kwargs.get("residual_severity_score")
    risk.residual_risk_score = kwargs.get("residual_risk_score")
    risk.potential_cost = kwargs.get("potential_cost")
    risk.currency = kwargs.get("currency", "MAD")
    risk.potential_delay_days = kwargs.get("potential_delay_days")
    risk.root_causes = kwargs.get("root_causes")
    risk.potential_effects = kwargs.get("potential_effects")
    risk.risk_triggers = kwargs.get("risk_triggers")
    risk.early_warning_signs = kwargs.get("early_warning_signs")
    risk.response_strategy = kwargs.get("response_strategy")
    risk.response_plan = kwargs.get("response_plan")
    risk.contingency_plan = kwargs.get("contingency_plan")
    risk.risk_owner_id = kwargs.get("risk_owner_id")
    risk.identified_date = kwargs.get("identified_date", datetime.now(timezone.utc))
    risk.target_resolution_date = kwargs.get("target_resolution_date")
    risk.actual_resolution_date = kwargs.get("actual_resolution_date")
    risk.last_review_date = kwargs.get("last_review_date")
    risk.next_review_date = kwargs.get("next_review_date")
    risk.occurred_date = kwargs.get("occurred_date")
    risk.actual_impact = kwargs.get("actual_impact")
    risk.actual_cost = kwargs.get("actual_cost")
    risk.lessons_learned = kwargs.get("lessons_learned")
    risk.notes = kwargs.get("notes")
    risk.tags = kwargs.get("tags", [])
    risk.deleted_at = kwargs.get("deleted_at")
    risk.created_at = kwargs.get("created_at", datetime.now(timezone.utc))
    risk.updated_at = kwargs.get("updated_at", datetime.now(timezone.utc))
    # Computed properties
    risk.risk_level = "medium" if inherent_risk_score >= 6 else "low"
    risk.is_open = status not in [
        RiskStatus.CLOSED.value,
        RiskStatus.OCCURRED.value,
        RiskStatus.ACCEPTED.value,
    ]
    return risk


def create_mock_mitigation(
    mitigation_id=None,
    risk_id=None,
    title="Test Mitigation",
    description="Test mitigation description",
    status=MitigationStatus.PLANNED.value,
    **kwargs,
):
    """Create a mock RiskMitigation object."""
    mitigation = MagicMock(spec=RiskMitigation)
    mitigation.id = mitigation_id or uuid4()
    mitigation.risk_id = risk_id or uuid4()
    mitigation.title = title
    mitigation.description = description
    mitigation.mitigation_type = kwargs.get("mitigation_type")
    mitigation.reduces_likelihood = kwargs.get("reduces_likelihood", True)
    mitigation.reduces_severity = kwargs.get("reduces_severity", False)
    mitigation.expected_likelihood_reduction = kwargs.get("expected_likelihood_reduction")
    mitigation.expected_severity_reduction = kwargs.get("expected_severity_reduction")
    mitigation.status = status
    mitigation.priority = kwargs.get("priority", "medium")
    mitigation.planned_start_date = kwargs.get("planned_start_date")
    mitigation.planned_end_date = kwargs.get("planned_end_date")
    mitigation.actual_start_date = kwargs.get("actual_start_date")
    mitigation.actual_end_date = kwargs.get("actual_end_date")
    mitigation.assigned_to_id = kwargs.get("assigned_to_id")
    mitigation.estimated_cost = kwargs.get("estimated_cost")
    mitigation.actual_cost = kwargs.get("actual_cost")
    mitigation.currency = kwargs.get("currency", "MAD")
    mitigation.effectiveness_rating = kwargs.get("effectiveness_rating")
    mitigation.effectiveness_notes = kwargs.get("effectiveness_notes")
    mitigation.completion_percentage = kwargs.get("completion_percentage", 0)
    mitigation.completion_notes = kwargs.get("completion_notes")
    mitigation.evidence = kwargs.get("evidence")
    mitigation.notes = kwargs.get("notes")
    mitigation.created_at = kwargs.get("created_at", datetime.now(timezone.utc))
    mitigation.updated_at = kwargs.get("updated_at", datetime.now(timezone.utc))
    # Computed properties
    mitigation.is_complete = status == MitigationStatus.COMPLETED.value
    mitigation.is_overdue = False
    return mitigation


# =============================================================================
# Risk CRUD Tests
# =============================================================================


class TestRiskCRUD:
    """Tests for Risk CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_risk_success(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test successful risk creation."""
        data = RiskCreate(
            risk_number="RISK-0001",
            title="Supply Chain Delay",
            description="Risk of supply chain delays due to vendor issues",
            category=RiskCategory.SUPPLY_CHAIN,
            inherent_likelihood=RiskLikelihood.LIKELY,
            inherent_severity=RiskSeverity.MAJOR,
        )

        # Mock no duplicate
        mock_db.execute.return_value = make_result(scalar_one_or_none=None)

        async def mock_refresh(obj, *args):
            obj.id = uuid4()
            obj.status = RiskStatus.IDENTIFIED.value
            obj.deleted_at = None
            obj.inherent_likelihood_score = 4
            obj.inherent_severity_score = 4
            obj.inherent_risk_score = 16
            # risk_level and is_open are computed properties - don't set them
            obj.created_at = datetime.now(timezone.utc)
            obj.updated_at = datetime.now(timezone.utc)
        mock_db.refresh = mock_refresh

        response = await create_risk(data, mock_db, mock_user)

        assert response.success is True
        assert response.message == "Risk created successfully"
        assert response.data.risk_number == "RISK-0001"
        assert response.data.title == "Supply Chain Delay"

    @pytest.mark.asyncio
    async def test_create_risk_duplicate_number(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test risk creation fails on duplicate number."""
        data = RiskCreate(
            risk_number="RISK-0001",
            title="Test Risk",
            description="Test description",
        )

        existing = create_mock_risk(risk_number="RISK-0001")
        mock_db.execute.return_value = make_result(scalar_one_or_none=existing)

        with pytest.raises(ConflictError):
            await create_risk(data, mock_db, mock_user)

    @pytest.mark.asyncio
    async def test_get_risk_success(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test getting risk by ID."""
        risk_id = uuid4()
        risk = create_mock_risk(risk_id=risk_id, title="Retrieved Risk")
        mock_db.execute.return_value = make_result(scalar_one_or_none=risk)

        response = await get_risk(risk_id, mock_db, mock_user)

        assert response.success is True
        assert response.data.id == risk_id
        assert response.data.title == "Retrieved Risk"

    @pytest.mark.asyncio
    async def test_get_risk_not_found(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test getting non-existent risk."""
        mock_db.execute.return_value = make_result(scalar_one_or_none=None)

        with pytest.raises(NotFoundError):
            await get_risk(uuid4(), mock_db, mock_user)

    @pytest.mark.asyncio
    async def test_list_risks(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test listing risks."""
        risks = [
            create_mock_risk(title="Risk One"),
            create_mock_risk(title="Risk Two"),
        ]

        mock_db.execute.side_effect = [
            make_result(scalar_one=2),
            make_result(scalars_all=risks),
        ]

        response = await list_risks(mock_db, mock_user, page=1, page_size=20)

        assert response.success is True
        assert len(response.data) == 2
        assert response.pagination.total_items == 2

    @pytest.mark.asyncio
    async def test_list_risks_filter_by_category(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test filtering risks by category."""
        risks = [create_mock_risk(category=RiskCategory.TECHNICAL.value)]

        mock_db.execute.side_effect = [
            make_result(scalar_one=1),
            make_result(scalars_all=risks),
        ]

        response = await list_risks(
            mock_db, mock_user, category=RiskCategory.TECHNICAL, page=1, page_size=20
        )

        assert response.success is True
        assert len(response.data) == 1

    @pytest.mark.asyncio
    async def test_update_risk(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test updating a risk."""
        risk_id = uuid4()
        risk = create_mock_risk(risk_id=risk_id, title="Original Title")
        mock_db.execute.return_value = make_result(scalar_one_or_none=risk)

        data = RiskUpdate(title="Updated Title", notes="New notes")

        async def mock_refresh(obj, *args):
            obj.title = "Updated Title"
            obj.notes = "New notes"
        mock_db.refresh = mock_refresh

        response = await update_risk(risk_id, data, mock_db, mock_user)

        assert response.success is True
        assert response.message == "Risk updated successfully"

    @pytest.mark.asyncio
    async def test_delete_risk(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test soft deleting a risk."""
        risk_id = uuid4()
        risk = create_mock_risk(risk_id=risk_id)
        mock_db.execute.return_value = make_result(scalar_one_or_none=risk)

        response = await delete_risk(risk_id, mock_db, mock_user)

        assert response.success is True
        assert response.message == "Risk deleted successfully"


# =============================================================================
# Risk Workflow Tests
# =============================================================================


class TestRiskWorkflow:
    """Tests for Risk workflow transitions."""

    @pytest.mark.asyncio
    async def test_analyze_risk(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test starting risk analysis."""
        risk_id = uuid4()
        risk = create_mock_risk(risk_id=risk_id, status=RiskStatus.IDENTIFIED.value)
        mock_db.execute.return_value = make_result(scalar_one_or_none=risk)

        async def mock_refresh(obj, *args):
            obj.status = RiskStatus.ANALYZING.value
        mock_db.refresh = mock_refresh

        response = await analyze_risk(risk_id, mock_db, mock_user)

        assert response.success is True
        assert response.message == "Risk analysis started"

    @pytest.mark.asyncio
    async def test_analyze_risk_invalid_status(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test analyzing risk not in identified status."""
        risk_id = uuid4()
        risk = create_mock_risk(risk_id=risk_id, status=RiskStatus.ANALYZING.value)
        mock_db.execute.return_value = make_result(scalar_one_or_none=risk)

        with pytest.raises(ConflictError):
            await analyze_risk(risk_id, mock_db, mock_user)

    @pytest.mark.asyncio
    async def test_start_mitigation(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test starting risk mitigation."""
        risk_id = uuid4()
        risk = create_mock_risk(risk_id=risk_id, status=RiskStatus.ANALYZING.value)
        mock_db.execute.return_value = make_result(scalar_one_or_none=risk)

        async def mock_refresh(obj, *args):
            obj.status = RiskStatus.MITIGATING.value
        mock_db.refresh = mock_refresh

        response = await start_mitigation(risk_id, mock_db, mock_user)

        assert response.success is True
        assert response.message == "Risk mitigation started"

    @pytest.mark.asyncio
    async def test_monitor_risk(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test moving risk to monitoring."""
        risk_id = uuid4()
        risk = create_mock_risk(risk_id=risk_id, status=RiskStatus.MITIGATING.value)
        mock_db.execute.return_value = make_result(scalar_one_or_none=risk)

        data = ResidualAssessmentData(
            residual_likelihood=RiskLikelihood.UNLIKELY,
            residual_severity=RiskSeverity.MINOR,
        )

        async def mock_refresh(obj, *args):
            obj.status = RiskStatus.MONITORING.value
            obj.residual_likelihood = RiskLikelihood.UNLIKELY.value
            obj.residual_severity = RiskSeverity.MINOR.value
            obj.residual_likelihood_score = 2
            obj.residual_severity_score = 2
            obj.residual_risk_score = 4
        mock_db.refresh = mock_refresh

        response = await monitor_risk(risk_id, data, mock_db, mock_user)

        assert response.success is True
        assert response.message == "Risk moved to monitoring"

    @pytest.mark.asyncio
    async def test_close_risk(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test closing a risk."""
        risk_id = uuid4()
        risk = create_mock_risk(risk_id=risk_id, status=RiskStatus.MONITORING.value)
        mock_db.execute.return_value = make_result(scalar_one_or_none=risk)

        async def mock_refresh(obj, *args):
            obj.status = RiskStatus.CLOSED.value
            obj.actual_resolution_date = datetime.now(timezone.utc)
            obj.is_open = False
        mock_db.refresh = mock_refresh

        response = await close_risk(risk_id, mock_db, mock_user)

        assert response.success is True
        assert response.message == "Risk closed"

    @pytest.mark.asyncio
    async def test_accept_risk(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test accepting a risk."""
        risk_id = uuid4()
        risk = create_mock_risk(risk_id=risk_id, status=RiskStatus.IDENTIFIED.value)
        mock_db.execute.return_value = make_result(scalar_one_or_none=risk)

        async def mock_refresh(obj, *args):
            obj.status = RiskStatus.ACCEPTED.value
            obj.is_open = False
        mock_db.refresh = mock_refresh

        response = await accept_risk(risk_id, mock_db, mock_user)

        assert response.success is True
        assert response.message == "Risk accepted"

    @pytest.mark.asyncio
    async def test_record_occurrence(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test recording risk occurrence."""
        risk_id = uuid4()
        risk = create_mock_risk(risk_id=risk_id, status=RiskStatus.MONITORING.value)
        mock_db.execute.return_value = make_result(scalar_one_or_none=risk)

        data = OccurrenceData(
            actual_impact="Project delayed by 2 weeks",
            actual_cost=Decimal("50000.00"),
            lessons_learned="Earlier supplier qualification needed",
        )

        async def mock_refresh(obj, *args):
            obj.status = RiskStatus.OCCURRED.value
            obj.occurred_date = datetime.now(timezone.utc)
            obj.actual_impact = "Project delayed by 2 weeks"
            obj.actual_cost = Decimal("50000.00")
            obj.is_open = False
        mock_db.refresh = mock_refresh

        response = await record_occurrence(risk_id, data, mock_db, mock_user)

        assert response.success is True
        assert response.message == "Risk occurrence recorded"

    @pytest.mark.asyncio
    async def test_record_review(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test recording a risk review."""
        risk_id = uuid4()
        risk = create_mock_risk(risk_id=risk_id, status=RiskStatus.MONITORING.value)
        mock_db.execute.return_value = make_result(scalar_one_or_none=risk)

        async def mock_refresh(obj, *args):
            obj.last_review_date = datetime.now(timezone.utc)
        mock_db.refresh = mock_refresh

        response = await record_review(risk_id, mock_db, mock_user, next_review_date=None)

        assert response.success is True
        assert response.message == "Risk review recorded"


# =============================================================================
# Risk Mitigation Tests
# =============================================================================


class TestRiskMitigations:
    """Tests for Risk mitigation operations."""

    @pytest.mark.asyncio
    async def test_add_mitigation(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test adding a mitigation."""
        risk_id = uuid4()
        risk = create_mock_risk(risk_id=risk_id)
        mock_db.execute.return_value = make_result(scalar_one_or_none=risk)

        data = MitigationCreate(
            title="Qualify alternate supplier",
            description="Identify and qualify a backup supplier",
            priority="high",
            reduces_likelihood=True,
        )

        async def mock_refresh(obj, *args):
            obj.id = uuid4()
            obj.status = MitigationStatus.PLANNED.value
            obj.completion_percentage = 0
            # is_complete and is_overdue are computed properties - don't set them
            obj.created_at = datetime.now(timezone.utc)
            obj.updated_at = datetime.now(timezone.utc)
        mock_db.refresh = mock_refresh

        response = await add_mitigation(risk_id, data, mock_db, mock_user)

        assert response.success is True
        assert response.message == "Mitigation created successfully"

    @pytest.mark.asyncio
    async def test_add_mitigation_risk_not_found(
        self, mock_db: AsyncMock, mock_user: MagicMock
    ):
        """Test adding mitigation for non-existent risk."""
        mock_db.execute.return_value = make_result(scalar_one_or_none=None)

        data = MitigationCreate(
            title="Test Mitigation",
            description="Test description",
        )

        with pytest.raises(NotFoundError):
            await add_mitigation(uuid4(), data, mock_db, mock_user)

    @pytest.mark.asyncio
    async def test_list_mitigations(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test listing mitigations."""
        risk_id = uuid4()
        risk = create_mock_risk(risk_id=risk_id)
        mitigations = [
            create_mock_mitigation(risk_id=risk_id),
            create_mock_mitigation(risk_id=risk_id),
        ]

        mock_db.execute.side_effect = [
            make_result(scalar_one_or_none=risk),
            make_result(scalar_one=2),
            make_result(scalars_all=mitigations),
        ]

        response = await list_mitigations(risk_id, mock_db, mock_user, page=1, page_size=20)

        assert response.success is True
        assert len(response.data) == 2

    @pytest.mark.asyncio
    async def test_get_mitigation(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test getting a specific mitigation."""
        risk_id = uuid4()
        mitigation_id = uuid4()
        mitigation = create_mock_mitigation(
            mitigation_id=mitigation_id, risk_id=risk_id
        )
        mock_db.execute.return_value = make_result(scalar_one_or_none=mitigation)

        response = await get_mitigation(risk_id, mitigation_id, mock_db, mock_user)

        assert response.success is True
        assert response.data.id == mitigation_id

    @pytest.mark.asyncio
    async def test_update_mitigation(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test updating a mitigation."""
        risk_id = uuid4()
        mitigation_id = uuid4()
        mitigation = create_mock_mitigation(
            mitigation_id=mitigation_id, risk_id=risk_id
        )
        mock_db.execute.return_value = make_result(scalar_one_or_none=mitigation)

        data = MitigationUpdate(priority="high", notes="Updated notes")

        async def mock_refresh(obj, *args):
            obj.priority = "high"
            obj.notes = "Updated notes"
        mock_db.refresh = mock_refresh

        response = await update_mitigation(
            risk_id, mitigation_id, data, mock_db, mock_user
        )

        assert response.success is True
        assert response.message == "Mitigation updated successfully"

    @pytest.mark.asyncio
    async def test_complete_mitigation(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test completing a mitigation."""
        risk_id = uuid4()
        mitigation_id = uuid4()
        mitigation = create_mock_mitigation(
            mitigation_id=mitigation_id,
            risk_id=risk_id,
            status=MitigationStatus.IN_PROGRESS.value,
        )
        mock_db.execute.return_value = make_result(scalar_one_or_none=mitigation)

        async def mock_refresh(obj, *args):
            obj.status = MitigationStatus.COMPLETED.value
            obj.completion_percentage = 100
            # is_complete is computed - don't set
            obj.actual_end_date = datetime.now(timezone.utc)
        mock_db.refresh = mock_refresh

        response = await complete_mitigation(
            risk_id, mitigation_id, mock_db, mock_user,
            effectiveness_rating=None, effectiveness_notes=None
        )

        assert response.success is True
        assert response.message == "Mitigation completed"

    @pytest.mark.asyncio
    async def test_complete_mitigation_already_complete(
        self, mock_db: AsyncMock, mock_user: MagicMock
    ):
        """Test completing already completed mitigation."""
        risk_id = uuid4()
        mitigation_id = uuid4()
        mitigation = create_mock_mitigation(
            mitigation_id=mitigation_id,
            risk_id=risk_id,
            status=MitigationStatus.COMPLETED.value,
        )
        mock_db.execute.return_value = make_result(scalar_one_or_none=mitigation)

        with pytest.raises(ConflictError):
            await complete_mitigation(risk_id, mitigation_id, mock_db, mock_user)

    @pytest.mark.asyncio
    async def test_delete_mitigation(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test deleting a mitigation."""
        risk_id = uuid4()
        mitigation_id = uuid4()
        mitigation = create_mock_mitigation(
            mitigation_id=mitigation_id, risk_id=risk_id
        )
        mock_db.execute.return_value = make_result(scalar_one_or_none=mitigation)

        response = await delete_mitigation(risk_id, mitigation_id, mock_db, mock_user)

        assert response.success is True
        assert response.message == "Mitigation deleted successfully"


# =============================================================================
# Risk Query Tests
# =============================================================================


class TestRiskQueries:
    """Tests for Risk query endpoints."""

    @pytest.mark.asyncio
    async def test_get_risk_by_number(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test getting risk by document number."""
        risk = create_mock_risk(risk_number="RISK-UNIQUE-001")
        mock_db.execute.return_value = make_result(scalar_one_or_none=risk)

        response = await get_risk_by_number("RISK-UNIQUE-001", mock_db, mock_user)

        assert response.success is True
        assert response.data.risk_number == "RISK-UNIQUE-001"

    @pytest.mark.asyncio
    async def test_get_risk_by_number_not_found(
        self, mock_db: AsyncMock, mock_user: MagicMock
    ):
        """Test getting non-existent risk by number."""
        mock_db.execute.return_value = make_result(scalar_one_or_none=None)

        with pytest.raises(NotFoundError):
            await get_risk_by_number("RISK-NOTEXIST", mock_db, mock_user)

    @pytest.mark.asyncio
    async def test_get_high_priority_risks(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test getting high priority risks."""
        risks = [
            create_mock_risk(title="High 1", inherent_risk_score=16),
            create_mock_risk(title="High 2", inherent_risk_score=20),
        ]

        mock_db.execute.side_effect = [
            make_result(scalar_one=2),
            make_result(scalars_all=risks),
        ]

        response = await get_high_priority_risks(mock_db, mock_user, page=1, page_size=20)

        assert response.success is True
        assert len(response.data) == 2

    @pytest.mark.asyncio
    async def test_get_open_risks(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test getting open risks."""
        risks = [
            create_mock_risk(title="Open 1", status=RiskStatus.IDENTIFIED.value),
            create_mock_risk(title="Open 2", status=RiskStatus.MITIGATING.value),
        ]

        mock_db.execute.side_effect = [
            make_result(scalar_one=2),
            make_result(scalars_all=risks),
        ]

        response = await get_open_risks(mock_db, mock_user, page=1, page_size=20)

        assert response.success is True
        assert len(response.data) == 2
