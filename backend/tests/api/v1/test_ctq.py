"""Tests for CTQ API endpoints.

Tests cover:
- CTQ CRUD operations
- CTQ workflow transitions (activate, submit, approve, obsolete)
- CTQ measurements (record, list, update, delete)
- Query endpoints
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from sensei.api.v1.endpoints.ctq import (
    router,
    create_ctq,
    get_ctq,
    list_ctqs,
    update_ctq,
    delete_ctq,
    activate_ctq,
    submit_for_review,
    approve_ctq,
    obsolete_ctq,
    create_measurement,
    list_measurements,
    get_measurement,
    update_measurement,
    delete_measurement,
    get_ctq_by_number,
    get_critical_ctqs,
    CTQCreate,
    CTQUpdate,
    MeasurementCreate,
    MeasurementUpdate,
)
from sensei.api.exceptions import ConflictError, NotFoundError
from sensei.models.ctq import (
    CTQ,
    CTQMeasurement,
    CTQCategory,
    CTQPriority,
    CTQStatus,
    MeasurementResult,
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


def create_mock_ctq(
    ctq_id=None,
    ctq_number="CTQ-0001",
    name="Test CTQ",
    category=CTQCategory.DIMENSIONAL.value,
    priority=CTQPriority.MAJOR.value,
    status=CTQStatus.DRAFT.value,
    nominal_value=None,
    upper_spec_limit=None,
    lower_spec_limit=None,
    is_customer_critical=False,
    **kwargs,
):
    """Create a mock CTQ object."""
    ctq = MagicMock(spec=CTQ)
    ctq.id = ctq_id or uuid4()
    ctq.ctq_number = ctq_number
    ctq.name = name
    ctq.description = kwargs.get("description")
    ctq.rfq_id = kwargs.get("rfq_id")
    ctq.part_number = kwargs.get("part_number")
    ctq.drawing_reference = kwargs.get("drawing_reference")
    ctq.operation_number = kwargs.get("operation_number")
    ctq.category = category
    ctq.priority = priority
    ctq.status = status
    ctq.nominal_value = nominal_value
    ctq.unit_of_measure = kwargs.get("unit_of_measure", "mm")
    ctq.upper_spec_limit = upper_spec_limit
    ctq.lower_spec_limit = lower_spec_limit
    ctq.tolerance_type = kwargs.get("tolerance_type")
    ctq.gdt_symbol = kwargs.get("gdt_symbol")
    ctq.gdt_value = kwargs.get("gdt_value")
    ctq.datum_reference = kwargs.get("datum_reference")
    ctq.target_cpk = kwargs.get("target_cpk")
    ctq.target_ppk = kwargs.get("target_ppk")
    ctq.sample_size = kwargs.get("sample_size")
    ctq.sample_frequency = kwargs.get("sample_frequency")
    ctq.measurement_method = kwargs.get("measurement_method")
    ctq.measurement_equipment = kwargs.get("measurement_equipment")
    ctq.gauge_id = kwargs.get("gauge_id")
    ctq.gauge_r_and_r = kwargs.get("gauge_r_and_r")
    ctq.control_method = kwargs.get("control_method")
    ctq.reaction_plan = kwargs.get("reaction_plan")
    ctq.customer_requirement = kwargs.get("customer_requirement")
    ctq.customer_specification = kwargs.get("customer_specification")
    ctq.is_customer_critical = is_customer_critical
    ctq.approved_by_id = kwargs.get("approved_by_id")
    ctq.approved_at = kwargs.get("approved_at")
    ctq.notes = kwargs.get("notes")
    ctq.custom_fields = kwargs.get("custom_fields")
    ctq.is_deleted = kwargs.get("is_deleted", False)
    ctq.created_at = kwargs.get("created_at", datetime.now(timezone.utc))
    ctq.updated_at = kwargs.get("updated_at", datetime.now(timezone.utc))
    # Computed property
    if upper_spec_limit is not None and lower_spec_limit is not None:
        ctq.tolerance_range = upper_spec_limit - lower_spec_limit
    else:
        ctq.tolerance_range = None
    return ctq


def create_mock_measurement(
    measurement_id=None,
    ctq_id=None,
    measured_value=Decimal("10.05"),
    result=MeasurementResult.PASS.value,
    **kwargs,
):
    """Create a mock CTQMeasurement object."""
    measurement = MagicMock(spec=CTQMeasurement)
    measurement.id = measurement_id or uuid4()
    measurement.ctq_id = ctq_id or uuid4()
    measurement.measurement_number = kwargs.get("measurement_number")
    measurement.batch_number = kwargs.get("batch_number")
    measurement.serial_number = kwargs.get("serial_number")
    measurement.sample_number = kwargs.get("sample_number")
    measurement.measured_value = measured_value
    measurement.deviation = kwargs.get("deviation")
    measurement.result = result
    measurement.measured_at = kwargs.get("measured_at", datetime.now(timezone.utc))
    measurement.measured_by_id = kwargs.get("measured_by_id")
    measurement.equipment_id = kwargs.get("equipment_id")
    measurement.calibration_date = kwargs.get("calibration_date")
    measurement.temperature = kwargs.get("temperature")
    measurement.humidity = kwargs.get("humidity")
    measurement.notes = kwargs.get("notes")
    measurement.corrective_action = kwargs.get("corrective_action")
    measurement.disposition = kwargs.get("disposition")
    measurement.attachments = kwargs.get("attachments")
    measurement.created_at = kwargs.get("created_at", datetime.now(timezone.utc))
    measurement.updated_at = kwargs.get("updated_at", datetime.now(timezone.utc))
    return measurement


# =============================================================================
# CTQ CRUD Tests
# =============================================================================


class TestCTQCRUD:
    """Tests for CTQ CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_ctq_success(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test successful CTQ creation."""
        data = CTQCreate(
            ctq_number="CTQ-0001",
            name="Length Tolerance",
            category=CTQCategory.DIMENSIONAL,
            priority=CTQPriority.CRITICAL,
            nominal_value=Decimal("100.00"),
            upper_spec_limit=Decimal("100.05"),
            lower_spec_limit=Decimal("99.95"),
            unit_of_measure="mm",
            is_customer_critical=True,
        )

        # Mock no duplicate
        mock_db.execute.return_value = make_result(scalar_one_or_none=None)

        async def mock_refresh(obj, *args):
            obj.id = uuid4()
            obj.status = CTQStatus.DRAFT.value
            obj.deleted_at = None  # is_deleted is computed from deleted_at
            # tolerance_range is computed from upper_spec_limit - lower_spec_limit
            obj.created_at = datetime.now(timezone.utc)
            obj.updated_at = datetime.now(timezone.utc)
        mock_db.refresh = mock_refresh

        response = await create_ctq(data, mock_db, mock_user)

        assert response.success is True
        assert response.message == "CTQ created successfully"
        assert response.data.ctq_number == "CTQ-0001"
        assert response.data.name == "Length Tolerance"

    @pytest.mark.asyncio
    async def test_create_ctq_duplicate_number(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test CTQ creation fails on duplicate number."""
        data = CTQCreate(
            ctq_number="CTQ-0001",
            name="Test CTQ",
        )

        existing = create_mock_ctq(ctq_number="CTQ-0001")
        mock_db.execute.return_value = make_result(scalar_one_or_none=existing)

        with pytest.raises(ConflictError):
            await create_ctq(data, mock_db, mock_user)

    @pytest.mark.asyncio
    async def test_get_ctq_success(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test getting CTQ by ID."""
        ctq_id = uuid4()
        ctq = create_mock_ctq(ctq_id=ctq_id, name="Retrieved CTQ")
        mock_db.execute.return_value = make_result(scalar_one_or_none=ctq)

        response = await get_ctq(ctq_id, mock_db, mock_user)

        assert response.success is True
        assert response.data.id == ctq_id
        assert response.data.name == "Retrieved CTQ"

    @pytest.mark.asyncio
    async def test_get_ctq_not_found(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test getting non-existent CTQ."""
        mock_db.execute.return_value = make_result(scalar_one_or_none=None)

        with pytest.raises(NotFoundError):
            await get_ctq(uuid4(), mock_db, mock_user)

    @pytest.mark.asyncio
    async def test_list_ctqs(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test listing CTQs."""
        ctqs = [
            create_mock_ctq(name="CTQ One"),
            create_mock_ctq(name="CTQ Two"),
        ]

        mock_db.execute.side_effect = [
            make_result(scalar_one=2),
            make_result(scalars_all=ctqs),
        ]

        response = await list_ctqs(mock_db, mock_user, page=1, page_size=20)

        assert response.success is True
        assert len(response.data) == 2
        assert response.pagination.total_items == 2

    @pytest.mark.asyncio
    async def test_list_ctqs_filter_by_category(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test filtering CTQs by category."""
        ctqs = [create_mock_ctq(category=CTQCategory.DIMENSIONAL.value)]

        mock_db.execute.side_effect = [
            make_result(scalar_one=1),
            make_result(scalars_all=ctqs),
        ]

        response = await list_ctqs(
            mock_db, mock_user, category=CTQCategory.DIMENSIONAL, page=1, page_size=20
        )

        assert response.success is True
        assert len(response.data) == 1

    @pytest.mark.asyncio
    async def test_update_ctq(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test updating a CTQ."""
        ctq_id = uuid4()
        ctq = create_mock_ctq(ctq_id=ctq_id, name="Original Name")
        mock_db.execute.return_value = make_result(scalar_one_or_none=ctq)

        data = CTQUpdate(name="Updated Name", notes="New notes")

        async def mock_refresh(obj, *args):
            obj.name = "Updated Name"
            obj.notes = "New notes"
        mock_db.refresh = mock_refresh

        response = await update_ctq(ctq_id, data, mock_db, mock_user)

        assert response.success is True
        assert response.message == "CTQ updated successfully"

    @pytest.mark.asyncio
    async def test_delete_ctq(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test soft deleting a CTQ."""
        ctq_id = uuid4()
        ctq = create_mock_ctq(ctq_id=ctq_id)
        mock_db.execute.return_value = make_result(scalar_one_or_none=ctq)

        response = await delete_ctq(ctq_id, mock_db, mock_user)

        assert response.success is True
        assert response.message == "CTQ deleted successfully"


# =============================================================================
# CTQ Workflow Tests
# =============================================================================


class TestCTQWorkflow:
    """Tests for CTQ workflow transitions."""

    @pytest.mark.asyncio
    async def test_activate_ctq(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test activating a CTQ."""
        ctq_id = uuid4()
        ctq = create_mock_ctq(ctq_id=ctq_id, status=CTQStatus.DRAFT.value)
        mock_db.execute.return_value = make_result(scalar_one_or_none=ctq)

        async def mock_refresh(obj, *args):
            obj.status = CTQStatus.ACTIVE.value
        mock_db.refresh = mock_refresh

        response = await activate_ctq(ctq_id, mock_db, mock_user)

        assert response.success is True
        assert response.message == "CTQ activated"

    @pytest.mark.asyncio
    async def test_activate_ctq_invalid_status(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test activating CTQ not in draft status."""
        ctq_id = uuid4()
        ctq = create_mock_ctq(ctq_id=ctq_id, status=CTQStatus.ACTIVE.value)
        mock_db.execute.return_value = make_result(scalar_one_or_none=ctq)

        with pytest.raises(ConflictError):
            await activate_ctq(ctq_id, mock_db, mock_user)

    @pytest.mark.asyncio
    async def test_submit_for_review(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test submitting CTQ for review."""
        ctq_id = uuid4()
        ctq = create_mock_ctq(ctq_id=ctq_id, status=CTQStatus.ACTIVE.value)
        mock_db.execute.return_value = make_result(scalar_one_or_none=ctq)

        async def mock_refresh(obj, *args):
            obj.status = CTQStatus.UNDER_REVIEW.value
        mock_db.refresh = mock_refresh

        response = await submit_for_review(ctq_id, mock_db, mock_user)

        assert response.success is True
        assert response.message == "CTQ submitted for review"

    @pytest.mark.asyncio
    async def test_approve_ctq(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test approving a CTQ."""
        ctq_id = uuid4()
        ctq = create_mock_ctq(ctq_id=ctq_id, status=CTQStatus.UNDER_REVIEW.value)
        mock_db.execute.return_value = make_result(scalar_one_or_none=ctq)

        async def mock_refresh(obj, *args):
            obj.status = CTQStatus.APPROVED.value
            obj.approved_by_id = mock_user.id
            obj.approved_at = datetime.now(timezone.utc)
        mock_db.refresh = mock_refresh

        response = await approve_ctq(ctq_id, mock_db, mock_user)

        assert response.success is True
        assert response.message == "CTQ approved"

    @pytest.mark.asyncio
    async def test_approve_ctq_invalid_status(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test approving CTQ not under review."""
        ctq_id = uuid4()
        ctq = create_mock_ctq(ctq_id=ctq_id, status=CTQStatus.DRAFT.value)
        mock_db.execute.return_value = make_result(scalar_one_or_none=ctq)

        with pytest.raises(ConflictError):
            await approve_ctq(ctq_id, mock_db, mock_user)

    @pytest.mark.asyncio
    async def test_obsolete_ctq(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test marking CTQ as obsolete."""
        ctq_id = uuid4()
        ctq = create_mock_ctq(ctq_id=ctq_id, status=CTQStatus.APPROVED.value)
        mock_db.execute.return_value = make_result(scalar_one_or_none=ctq)

        async def mock_refresh(obj, *args):
            obj.status = CTQStatus.OBSOLETE.value
        mock_db.refresh = mock_refresh

        response = await obsolete_ctq(ctq_id, mock_db, mock_user)

        assert response.success is True
        assert response.message == "CTQ marked obsolete"


# =============================================================================
# CTQ Measurement Tests
# =============================================================================


class TestCTQMeasurements:
    """Tests for CTQ measurement operations."""

    @pytest.mark.asyncio
    async def test_create_measurement(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test creating a measurement."""
        ctq_id = uuid4()
        ctq = create_mock_ctq(
            ctq_id=ctq_id,
            nominal_value=Decimal("10.00"),
            upper_spec_limit=Decimal("10.10"),
            lower_spec_limit=Decimal("9.90"),
        )
        mock_db.execute.return_value = make_result(scalar_one_or_none=ctq)

        data = MeasurementCreate(
            measured_value=Decimal("10.05"),
            batch_number="BATCH-001",
        )

        async def mock_refresh(obj, *args):
            obj.id = uuid4()
            obj.result = MeasurementResult.PASS.value
            obj.deviation = Decimal("0.05")
            obj.created_at = datetime.now(timezone.utc)
            obj.updated_at = datetime.now(timezone.utc)
        mock_db.refresh = mock_refresh

        response = await create_measurement(ctq_id, data, mock_db, mock_user)

        assert response.success is True
        assert response.message == "Measurement created successfully"

    @pytest.mark.asyncio
    async def test_create_measurement_ctq_not_found(
        self, mock_db: AsyncMock, mock_user: MagicMock
    ):
        """Test creating measurement for non-existent CTQ."""
        mock_db.execute.return_value = make_result(scalar_one_or_none=None)

        data = MeasurementCreate(measured_value=Decimal("10.05"))

        with pytest.raises(NotFoundError):
            await create_measurement(uuid4(), data, mock_db, mock_user)

    @pytest.mark.asyncio
    async def test_list_measurements(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test listing measurements."""
        ctq_id = uuid4()
        ctq = create_mock_ctq(ctq_id=ctq_id)
        measurements = [
            create_mock_measurement(ctq_id=ctq_id),
            create_mock_measurement(ctq_id=ctq_id),
        ]

        # Three db.execute calls: check CTQ, count, data
        mock_db.execute.side_effect = [
            make_result(scalar_one_or_none=ctq),
            make_result(scalar_one=2),
            make_result(scalars_all=measurements),
        ]

        response = await list_measurements(ctq_id, mock_db, mock_user, page=1, page_size=20)

        assert response.success is True
        assert len(response.data) == 2

    @pytest.mark.asyncio
    async def test_get_measurement(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test getting a specific measurement."""
        ctq_id = uuid4()
        measurement_id = uuid4()
        measurement = create_mock_measurement(
            measurement_id=measurement_id, ctq_id=ctq_id
        )
        mock_db.execute.return_value = make_result(scalar_one_or_none=measurement)

        response = await get_measurement(ctq_id, measurement_id, mock_db, mock_user)

        assert response.success is True
        assert response.data.id == measurement_id

    @pytest.mark.asyncio
    async def test_update_measurement(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test updating a measurement."""
        ctq_id = uuid4()
        measurement_id = uuid4()
        measurement = create_mock_measurement(
            measurement_id=measurement_id, ctq_id=ctq_id
        )
        mock_db.execute.return_value = make_result(scalar_one_or_none=measurement)

        data = MeasurementUpdate(notes="Updated notes", disposition="accept")

        async def mock_refresh(obj, *args):
            obj.notes = "Updated notes"
            obj.disposition = "accept"
        mock_db.refresh = mock_refresh

        response = await update_measurement(
            ctq_id, measurement_id, data, mock_db, mock_user
        )

        assert response.success is True
        assert response.message == "Measurement updated successfully"

    @pytest.mark.asyncio
    async def test_delete_measurement(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test deleting a measurement."""
        ctq_id = uuid4()
        measurement_id = uuid4()
        measurement = create_mock_measurement(
            measurement_id=measurement_id, ctq_id=ctq_id
        )
        mock_db.execute.return_value = make_result(scalar_one_or_none=measurement)

        response = await delete_measurement(ctq_id, measurement_id, mock_db, mock_user)

        assert response.success is True
        assert response.message == "Measurement deleted successfully"


# =============================================================================
# CTQ Query Tests
# =============================================================================


class TestCTQQueries:
    """Tests for CTQ query endpoints."""

    @pytest.mark.asyncio
    async def test_get_ctq_by_number(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test getting CTQ by document number."""
        ctq = create_mock_ctq(ctq_number="CTQ-UNIQUE-001")
        mock_db.execute.return_value = make_result(scalar_one_or_none=ctq)

        response = await get_ctq_by_number("CTQ-UNIQUE-001", mock_db, mock_user)

        assert response.success is True
        assert response.data.ctq_number == "CTQ-UNIQUE-001"

    @pytest.mark.asyncio
    async def test_get_ctq_by_number_not_found(
        self, mock_db: AsyncMock, mock_user: MagicMock
    ):
        """Test getting non-existent CTQ by number."""
        mock_db.execute.return_value = make_result(scalar_one_or_none=None)

        with pytest.raises(NotFoundError):
            await get_ctq_by_number("CTQ-NOTEXIST", mock_db, mock_user)

    @pytest.mark.asyncio
    async def test_get_critical_ctqs(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test getting customer-critical CTQs."""
        ctqs = [
            create_mock_ctq(name="Critical 1", is_customer_critical=True),
            create_mock_ctq(name="Critical 2", is_customer_critical=True),
        ]

        mock_db.execute.side_effect = [
            make_result(scalar_one=2),
            make_result(scalars_all=ctqs),
        ]

        response = await get_critical_ctqs(mock_db, mock_user, page=1, page_size=20)

        assert response.success is True
        assert len(response.data) == 2
