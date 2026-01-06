"""Tests for Standard Work API endpoints."""

from datetime import datetime, date, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from sensei.api.exceptions import ConflictError, NotFoundError
from sensei.api.v1.endpoints.standard_work import (
    router,
    create_standard_work,
    get_standard_work,
    list_standard_works,
    update_standard_work,
    delete_standard_work,
    submit_for_approval,
    approve_standard_work,
    reject_standard_work,
    create_revision,
    mark_obsolete,
    update_content,
    list_versions,
    get_version,
    get_by_document_number,
    get_by_station,
    get_by_product,
    get_pending_review,
    get_expired,
    StandardWorkCreate,
    StandardWorkUpdate,
    StandardWorkSubmit,
    StandardWorkApprove,
    StandardWorkReject,
    StandardWorkRevise,
    ContentUpdate,
    ContentStep,
)
from sensei.models.standard_work import (
    StandardWork,
    StandardWorkStatus,
    StandardWorkType,
    StandardWorkVersion,
)


# =============================================================================
# Test Fixtures and Helpers
# =============================================================================


def make_result(
    scalar_one_or_none=None,
    scalars_all=None,
    scalar_one=None,
):
    """Create a mock result object."""
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=scalar_one_or_none)
    result.scalar_one = MagicMock(return_value=scalar_one if scalar_one is not None else 0)
    scalars_mock = MagicMock()
    scalars_mock.all = MagicMock(return_value=scalars_all or [])
    result.scalars = MagicMock(return_value=scalars_mock)
    return result


@pytest.fixture
def db():
    """Create mock database session."""
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.refresh = AsyncMock()
    mock_db.commit = AsyncMock()
    return mock_db


@pytest.fixture
def current_user():
    """Create mock current user."""
    user = MagicMock()
    user.id = uuid4()
    user.email = "test@example.com"
    user.full_name = "Test User"
    return user


# =============================================================================
# Standard Work CRUD Tests
# =============================================================================


@pytest.mark.asyncio
async def test_standard_work_crud(db, current_user):
    """Test standard work CRUD operations."""
    now = datetime.utcnow()
    today = date.today()
    
    # Create a standard work object for captures
    sw = None
    
    def capture_add(obj):
        nonlocal sw
        sw = obj
        obj.id = 1
        obj.document_number = "SW-001"
        obj.title = "Assembly Procedure"
        obj.description = "Test description"
        obj.version = 1
        obj.revision_code = "A"
        obj.document_type = StandardWorkType.WORK_INSTRUCTION
        obj.status = StandardWorkStatus.DRAFT
        obj.product_id = None
        obj.station_id = None
        obj.content_json = None
        obj.effective_date = None
        obj.expiration_date = None
        obj.review_date = None
        obj.submitted_by_id = None
        obj.submitted_at = None
        obj.approved_by_id = None
        obj.approved_at = None
        obj.approval_notes = None
        obj.change_summary = None
        obj.previous_version_id = None
        obj.requires_training = True
        obj.training_duration_minutes = 30
        obj.created_at = now
        obj.updated_at = now
        obj.deleted_at = None  # is_deleted is computed from this
        
    db.add.side_effect = capture_add
    
    # Test create - check for duplicate first, then create
    db.execute.side_effect = [
        make_result(scalar_one_or_none=None),  # No duplicate
    ]
    
    resp = await create_standard_work(
        StandardWorkCreate(
            document_number="SW-001",
            title="Assembly Procedure",
            description="Test description",
            document_type=StandardWorkType.WORK_INSTRUCTION,
        ),
        db,
        current_user,
    )
    assert resp.success is True
    assert resp.data.document_number == "SW-001"
    assert resp.data.status == StandardWorkStatus.DRAFT
    
    db.add.side_effect = None
    db.execute.side_effect = None
    
    # Test duplicate check
    existing_sw = MagicMock()
    existing_sw.id = 99
    db.execute.return_value = make_result(scalar_one_or_none=existing_sw)
    with pytest.raises(ConflictError):
        await create_standard_work(
            StandardWorkCreate(
                document_number="SW-001",
                title="Another Doc",
            ),
            db,
            current_user,
        )
    
    # Test get standard work - prepare mock with computed properties
    mock_sw = MagicMock(spec=StandardWork)
    mock_sw.id = 1
    mock_sw.document_number = "SW-001"
    mock_sw.title = "Assembly Procedure"
    mock_sw.description = "Test description"
    mock_sw.version = 1
    mock_sw.revision_code = "A"
    mock_sw.document_type = StandardWorkType.WORK_INSTRUCTION
    mock_sw.status = StandardWorkStatus.DRAFT
    mock_sw.product_id = None
    mock_sw.station_id = None
    mock_sw.content_json = {"steps": [{"sequence": 1, "instruction": "Step 1"}]}
    mock_sw.effective_date = None
    mock_sw.expiration_date = None
    mock_sw.review_date = None
    mock_sw.submitted_by_id = None
    mock_sw.submitted_at = None
    mock_sw.approved_by_id = None
    mock_sw.approved_at = None
    mock_sw.approval_notes = None
    mock_sw.change_summary = None
    mock_sw.previous_version_id = None
    mock_sw.requires_training = True
    mock_sw.training_duration_minutes = 30
    mock_sw.created_at = now
    mock_sw.updated_at = now
    mock_sw.is_deleted = False
    # Computed properties
    mock_sw.full_document_id = "SW-001-RevA"
    mock_sw.is_current = False
    mock_sw.is_expired = False
    mock_sw.needs_review = False
    mock_sw.step_count = 1
    
    db.execute.return_value = make_result(scalar_one_or_none=mock_sw)
    resp = await get_standard_work(1, db, current_user)
    assert resp.success is True
    assert resp.data.id == 1
    
    # Test get not found
    db.execute.return_value = make_result(scalar_one_or_none=None)
    with pytest.raises(NotFoundError):
        await get_standard_work(999, db, current_user)
    
    # Test update
    db.execute.return_value = make_result(scalar_one_or_none=mock_sw)
    resp = await update_standard_work(
        1,
        StandardWorkUpdate(title="Updated Title"),
        db,
        current_user,
    )
    assert resp.success is True
    
    # Test update non-draft fails
    mock_sw.status = StandardWorkStatus.APPROVED
    db.execute.return_value = make_result(scalar_one_or_none=mock_sw)
    with pytest.raises(ConflictError):
        await update_standard_work(
            1,
            StandardWorkUpdate(title="Changed"),
            db,
            current_user,
        )
    mock_sw.status = StandardWorkStatus.DRAFT  # Reset
    
    # Test delete
    db.execute.return_value = make_result(scalar_one_or_none=mock_sw)
    resp = await delete_standard_work(1, db, current_user)
    assert resp.success is True
    
    # Test delete not found
    db.execute.return_value = make_result(scalar_one_or_none=None)
    with pytest.raises(NotFoundError):
        await delete_standard_work(999, db, current_user)


@pytest.mark.asyncio
async def test_standard_work_list(db, current_user):
    """Test list standard works with filters."""
    now = datetime.utcnow()
    today = date.today()
    
    mock_sw1 = MagicMock(spec=StandardWork)
    mock_sw1.id = 1
    mock_sw1.document_number = "SW-001"
    mock_sw1.title = "First Doc"
    mock_sw1.description = None
    mock_sw1.version = 1
    mock_sw1.revision_code = "A"
    mock_sw1.document_type = StandardWorkType.WORK_INSTRUCTION
    mock_sw1.status = StandardWorkStatus.APPROVED
    mock_sw1.product_id = 1
    mock_sw1.station_id = 1
    mock_sw1.content_json = None
    mock_sw1.effective_date = None
    mock_sw1.expiration_date = None
    mock_sw1.review_date = None
    mock_sw1.submitted_by_id = None
    mock_sw1.submitted_at = None
    mock_sw1.approved_by_id = None
    mock_sw1.approved_at = None
    mock_sw1.approval_notes = None
    mock_sw1.change_summary = None
    mock_sw1.previous_version_id = None
    mock_sw1.requires_training = True
    mock_sw1.training_duration_minutes = 30
    mock_sw1.created_at = now
    mock_sw1.updated_at = now
    mock_sw1.is_deleted = False
    mock_sw1.full_document_id = "SW-001-RevA"
    mock_sw1.is_current = True
    mock_sw1.is_expired = False
    mock_sw1.needs_review = False
    mock_sw1.step_count = 0
    
    mock_sw2 = MagicMock(spec=StandardWork)
    mock_sw2.id = 2
    mock_sw2.document_number = "SW-002"
    mock_sw2.title = "Second Doc"
    mock_sw2.description = None
    mock_sw2.version = 1
    mock_sw2.revision_code = "A"
    mock_sw2.document_type = StandardWorkType.STANDARD_OPERATING_PROCEDURE
    mock_sw2.status = StandardWorkStatus.DRAFT
    mock_sw2.product_id = 2
    mock_sw2.station_id = 2
    mock_sw2.content_json = None
    mock_sw2.effective_date = None
    mock_sw2.expiration_date = None
    mock_sw2.review_date = None
    mock_sw2.submitted_by_id = None
    mock_sw2.submitted_at = None
    mock_sw2.approved_by_id = None
    mock_sw2.approved_at = None
    mock_sw2.approval_notes = None
    mock_sw2.change_summary = None
    mock_sw2.previous_version_id = None
    mock_sw2.requires_training = True
    mock_sw2.training_duration_minutes = 60
    mock_sw2.created_at = now
    mock_sw2.updated_at = now
    mock_sw2.is_deleted = False
    mock_sw2.full_document_id = "SW-002-RevA"
    mock_sw2.is_current = False
    mock_sw2.is_expired = False
    mock_sw2.needs_review = False
    mock_sw2.step_count = 0
    
    # Test basic list
    db.execute.side_effect = [
        make_result(scalar_one=2),  # count
        make_result(scalars_all=[mock_sw1, mock_sw2]),  # data
    ]
    
    resp = await list_standard_works(
        db,
        current_user,
        page=1,
        page_size=20,
    )
    assert resp.success is True
    assert resp.pagination.total_items == 2
    assert len(resp.data) == 2
    
    # Test with status filter
    db.execute.side_effect = [
        make_result(scalar_one=1),
        make_result(scalars_all=[mock_sw1]),
    ]
    
    resp = await list_standard_works(
        db,
        current_user,
        status=StandardWorkStatus.APPROVED,
        page=1,
        page_size=20,
    )
    assert resp.pagination.total_items == 1
    
    # Test with document_type filter
    db.execute.side_effect = [
        make_result(scalar_one=1),
        make_result(scalars_all=[mock_sw2]),
    ]
    
    resp = await list_standard_works(
        db,
        current_user,
        document_type=StandardWorkType.STANDARD_OPERATING_PROCEDURE,
        page=1,
        page_size=20,
    )
    assert resp.pagination.total_items == 1
    
    # Test with search
    db.execute.side_effect = [
        make_result(scalar_one=1),
        make_result(scalars_all=[mock_sw1]),
    ]
    
    resp = await list_standard_works(
        db,
        current_user,
        search="First",
        page=1,
        page_size=20,
    )
    assert resp.pagination.total_items == 1


# =============================================================================
# Standard Work Workflow Tests
# =============================================================================


@pytest.mark.asyncio
async def test_standard_work_workflow(db, current_user):
    """Test standard work document workflow operations."""
    now = datetime.utcnow()
    
    # Create a mock document in draft status
    mock_sw = MagicMock(spec=StandardWork)
    mock_sw.id = 1
    mock_sw.document_number = "SW-001"
    mock_sw.title = "Test Doc"
    mock_sw.description = None
    mock_sw.version = 1
    mock_sw.revision_code = "A"
    mock_sw.document_type = StandardWorkType.WORK_INSTRUCTION
    mock_sw.status = StandardWorkStatus.DRAFT
    mock_sw.product_id = None
    mock_sw.station_id = None
    mock_sw.content_json = {"steps": []}
    mock_sw.effective_date = None
    mock_sw.expiration_date = None
    mock_sw.review_date = None
    mock_sw.submitted_by_id = None
    mock_sw.submitted_at = None
    mock_sw.approved_by_id = None
    mock_sw.approved_at = None
    mock_sw.approval_notes = None
    mock_sw.change_summary = None
    mock_sw.previous_version_id = None
    mock_sw.requires_training = True
    mock_sw.training_duration_minutes = 30
    mock_sw.created_at = now
    mock_sw.updated_at = now
    mock_sw.is_deleted = False
    mock_sw.full_document_id = "SW-001-RevA"
    mock_sw.is_current = False
    mock_sw.is_expired = False
    mock_sw.needs_review = False
    mock_sw.step_count = 0
    mock_sw.can_submit_for_approval = MagicMock(return_value=True)
    mock_sw.can_approve = MagicMock(return_value=False)
    
    # Test submit for approval
    db.execute.return_value = make_result(scalar_one_or_none=mock_sw)
    resp = await submit_for_approval(
        1,
        StandardWorkSubmit(notes="Ready for review"),
        db,
        current_user,
    )
    assert resp.success is True
    
    # Test submit when not in draft
    mock_sw.can_submit_for_approval = MagicMock(return_value=False)
    mock_sw.status = StandardWorkStatus.PENDING_APPROVAL
    db.execute.return_value = make_result(scalar_one_or_none=mock_sw)
    with pytest.raises(ConflictError):
        await submit_for_approval(
            1,
            StandardWorkSubmit(),
            db,
            current_user,
        )
    
    # Test approve
    mock_sw.can_approve = MagicMock(return_value=True)
    version_captured = None
    def capture_version(obj):
        nonlocal version_captured
        version_captured = obj
    db.add.side_effect = capture_version
    
    db.execute.side_effect = [
        make_result(scalar_one_or_none=mock_sw),  # Get document
        make_result(scalars_all=[]),  # Get previous versions to supersede
    ]
    
    resp = await approve_standard_work(
        1,
        StandardWorkApprove(approval_notes="Approved"),
        db,
        current_user,
    )
    assert resp.success is True
    
    db.add.side_effect = None
    db.execute.side_effect = None
    
    # Test approve when not pending
    mock_sw.can_approve = MagicMock(return_value=False)
    mock_sw.status = StandardWorkStatus.DRAFT
    db.execute.return_value = make_result(scalar_one_or_none=mock_sw)
    with pytest.raises(ConflictError):
        await approve_standard_work(
            1,
            StandardWorkApprove(),
            db,
            current_user,
        )
    
    # Test reject
    mock_sw.status = StandardWorkStatus.PENDING_APPROVAL
    db.execute.return_value = make_result(scalar_one_or_none=mock_sw)
    resp = await reject_standard_work(
        1,
        StandardWorkReject(rejection_notes="Needs more detail"),
        db,
        current_user,
    )
    assert resp.success is True
    
    # Test reject when not pending
    mock_sw.status = StandardWorkStatus.DRAFT
    db.execute.return_value = make_result(scalar_one_or_none=mock_sw)
    with pytest.raises(ConflictError):
        await reject_standard_work(
            1,
            StandardWorkReject(rejection_notes="Can't reject draft"),
            db,
            current_user,
        )
    
    # Test create revision
    mock_sw.status = StandardWorkStatus.APPROVED
    new_sw = MagicMock(spec=StandardWork)
    new_sw.id = 2
    new_sw.document_number = "SW-001"
    new_sw.title = "Test Doc"
    new_sw.description = None
    new_sw.version = 2
    new_sw.revision_code = "B"
    new_sw.document_type = StandardWorkType.WORK_INSTRUCTION
    new_sw.status = StandardWorkStatus.DRAFT
    new_sw.product_id = None
    new_sw.station_id = None
    new_sw.content_json = {"steps": []}
    new_sw.effective_date = None
    new_sw.expiration_date = None
    new_sw.review_date = None
    new_sw.submitted_by_id = None
    new_sw.submitted_at = None
    new_sw.approved_by_id = None
    new_sw.approved_at = None
    new_sw.approval_notes = None
    new_sw.change_summary = "Minor updates"
    new_sw.previous_version_id = 1
    new_sw.requires_training = True
    new_sw.training_duration_minutes = 30
    new_sw.created_at = now
    new_sw.updated_at = now
    new_sw.is_deleted = False
    new_sw.full_document_id = "SW-001-RevB"
    new_sw.is_current = False
    new_sw.is_expired = False
    new_sw.needs_review = False
    new_sw.step_count = 0
    
    mock_sw.create_new_version = MagicMock(return_value=new_sw)
    
    db.execute.side_effect = [
        make_result(scalar_one_or_none=mock_sw),  # Get document
        make_result(scalar_one_or_none=None),  # Check for existing draft
    ]
    
    resp = await create_revision(
        1,
        StandardWorkRevise(change_summary="Minor updates"),
        db,
        current_user,
    )
    assert resp.success is True
    
    db.execute.side_effect = None
    
    # Test create revision when draft already exists
    db.execute.side_effect = [
        make_result(scalar_one_or_none=mock_sw),
        make_result(scalar_one_or_none=new_sw),  # Draft exists
    ]
    with pytest.raises(ConflictError):
        await create_revision(
            1,
            StandardWorkRevise(),
            db,
            current_user,
        )
    
    db.execute.side_effect = None
    
    # Test create revision when not approved
    mock_sw.status = StandardWorkStatus.DRAFT
    db.execute.return_value = make_result(scalar_one_or_none=mock_sw)
    with pytest.raises(ConflictError):
        await create_revision(
            1,
            StandardWorkRevise(),
            db,
            current_user,
        )
    
    # Test mark obsolete
    mock_sw.status = StandardWorkStatus.APPROVED
    db.execute.return_value = make_result(scalar_one_or_none=mock_sw)
    resp = await mark_obsolete(1, db, current_user)
    assert resp.success is True
    
    # Test mark obsolete when already obsolete
    mock_sw.status = StandardWorkStatus.OBSOLETE
    db.execute.return_value = make_result(scalar_one_or_none=mock_sw)
    with pytest.raises(ConflictError):
        await mark_obsolete(1, db, current_user)
    
    # Test mark obsolete when draft
    mock_sw.status = StandardWorkStatus.DRAFT
    db.execute.return_value = make_result(scalar_one_or_none=mock_sw)
    with pytest.raises(ConflictError):
        await mark_obsolete(1, db, current_user)


# =============================================================================
# Standard Work Content Tests
# =============================================================================


@pytest.mark.asyncio
async def test_standard_work_content(db, current_user):
    """Test content update operations."""
    now = datetime.utcnow()
    
    mock_sw = MagicMock(spec=StandardWork)
    mock_sw.id = 1
    mock_sw.document_number = "SW-001"
    mock_sw.title = "Test Doc"
    mock_sw.description = None
    mock_sw.version = 1
    mock_sw.revision_code = "A"
    mock_sw.document_type = StandardWorkType.WORK_INSTRUCTION
    mock_sw.status = StandardWorkStatus.DRAFT
    mock_sw.product_id = None
    mock_sw.station_id = None
    mock_sw.content_json = {}
    mock_sw.effective_date = None
    mock_sw.expiration_date = None
    mock_sw.review_date = None
    mock_sw.submitted_by_id = None
    mock_sw.submitted_at = None
    mock_sw.approved_by_id = None
    mock_sw.approved_at = None
    mock_sw.approval_notes = None
    mock_sw.change_summary = None
    mock_sw.previous_version_id = None
    mock_sw.requires_training = True
    mock_sw.training_duration_minutes = 30
    mock_sw.created_at = now
    mock_sw.updated_at = now
    mock_sw.is_deleted = False
    mock_sw.full_document_id = "SW-001-RevA"
    mock_sw.is_current = False
    mock_sw.is_expired = False
    mock_sw.needs_review = False
    mock_sw.step_count = 0
    
    # Test update content
    db.execute.return_value = make_result(scalar_one_or_none=mock_sw)
    resp = await update_content(
        1,
        ContentUpdate(
            steps=[
                ContentStep(
                    sequence=1,
                    instruction="First step",
                    critical=True,
                ),
                ContentStep(
                    sequence=2,
                    instruction="Second step",
                ),
            ],
            safety_warnings=["Wear PPE"],
            required_ppe=["Safety glasses"],
        ),
        db,
        current_user,
    )
    assert resp.success is True
    
    # Test update content when not draft
    mock_sw.status = StandardWorkStatus.APPROVED
    db.execute.return_value = make_result(scalar_one_or_none=mock_sw)
    with pytest.raises(ConflictError):
        await update_content(
            1,
            ContentUpdate(steps=[]),
            db,
            current_user,
        )
    
    # Test update content not found
    db.execute.return_value = make_result(scalar_one_or_none=None)
    with pytest.raises(NotFoundError):
        await update_content(
            999,
            ContentUpdate(),
            db,
            current_user,
        )


# =============================================================================
# Standard Work Version Tests
# =============================================================================


@pytest.mark.asyncio
async def test_standard_work_versions(db, current_user):
    """Test version history endpoints."""
    now = datetime.utcnow()
    user_id = uuid4()
    
    mock_sw = MagicMock(spec=StandardWork)
    mock_sw.id = 1
    
    mock_v1 = MagicMock(spec=StandardWorkVersion)
    mock_v1.id = 1
    mock_v1.standard_work_id = 1
    mock_v1.version = 1
    mock_v1.revision_code = "A"
    mock_v1.content_json = {"steps": []}
    mock_v1.change_summary = "Initial version"
    mock_v1.created_by_id = user_id
    mock_v1.created_at = now
    
    mock_v2 = MagicMock(spec=StandardWorkVersion)
    mock_v2.id = 2
    mock_v2.standard_work_id = 1
    mock_v2.version = 2
    mock_v2.revision_code = "B"
    mock_v2.content_json = {"steps": [{"sequence": 1, "instruction": "Step 1"}]}
    mock_v2.change_summary = "Added step"
    mock_v2.created_by_id = user_id
    mock_v2.created_at = now
    
    # Test list versions
    db.execute.side_effect = [
        make_result(scalar_one_or_none=mock_sw),  # Check document exists
        make_result(scalar_one=2),  # Count
        make_result(scalars_all=[mock_v2, mock_v1]),  # Data
    ]
    
    resp = await list_versions(1, db, current_user, page=1, page_size=20)
    assert resp.success is True
    assert resp.pagination.total_items == 2
    assert len(resp.data) == 2
    
    db.execute.side_effect = None
    
    # Test list versions not found
    db.execute.return_value = make_result(scalar_one_or_none=None)
    with pytest.raises(NotFoundError):
        await list_versions(999, db, current_user)
    
    # Test get specific version
    db.execute.return_value = make_result(scalar_one_or_none=mock_v1)
    resp = await get_version(1, 1, db, current_user)
    assert resp.success is True
    assert resp.data.version == 1
    
    # Test get version not found
    db.execute.return_value = make_result(scalar_one_or_none=None)
    with pytest.raises(NotFoundError):
        await get_version(1, 99, db, current_user)


# =============================================================================
# Standard Work Query Tests
# =============================================================================


@pytest.mark.asyncio
async def test_standard_work_queries(db, current_user):
    """Test query endpoints (by document number, station, product, etc.)."""
    now = datetime.utcnow()
    today = date.today()
    
    mock_sw = MagicMock(spec=StandardWork)
    mock_sw.id = 1
    mock_sw.document_number = "SW-001"
    mock_sw.title = "Test Doc"
    mock_sw.description = None
    mock_sw.version = 1
    mock_sw.revision_code = "A"
    mock_sw.document_type = StandardWorkType.WORK_INSTRUCTION
    mock_sw.status = StandardWorkStatus.APPROVED
    mock_sw.product_id = 1
    mock_sw.station_id = 1
    mock_sw.content_json = None
    mock_sw.effective_date = None
    mock_sw.expiration_date = None
    mock_sw.review_date = today - timedelta(days=1)  # Needs review
    mock_sw.submitted_by_id = None
    mock_sw.submitted_at = None
    mock_sw.approved_by_id = None
    mock_sw.approved_at = None
    mock_sw.approval_notes = None
    mock_sw.change_summary = None
    mock_sw.previous_version_id = None
    mock_sw.requires_training = True
    mock_sw.training_duration_minutes = 30
    mock_sw.created_at = now
    mock_sw.updated_at = now
    mock_sw.is_deleted = False
    mock_sw.full_document_id = "SW-001-RevA"
    mock_sw.is_current = True
    mock_sw.is_expired = False
    mock_sw.needs_review = True
    mock_sw.step_count = 0
    
    # Test get by document number
    db.execute.side_effect = [
        make_result(scalar_one=1),
        make_result(scalars_all=[mock_sw]),
    ]
    resp = await get_by_document_number("SW-001", db, current_user, page=1, page_size=20)
    assert resp.success is True
    assert resp.pagination.total_items == 1
    
    db.execute.side_effect = None
    
    # Test get by station
    db.execute.side_effect = [
        make_result(scalar_one=1),
        make_result(scalars_all=[mock_sw]),
    ]
    resp = await get_by_station(1, db, current_user, page=1, page_size=20)
    assert resp.success is True
    assert resp.pagination.total_items == 1
    
    db.execute.side_effect = None
    
    # Test get by product
    db.execute.side_effect = [
        make_result(scalar_one=1),
        make_result(scalars_all=[mock_sw]),
    ]
    resp = await get_by_product(1, db, current_user, page=1, page_size=20)
    assert resp.success is True
    assert resp.pagination.total_items == 1
    
    db.execute.side_effect = None
    
    # Test get pending review
    db.execute.side_effect = [
        make_result(scalar_one=1),
        make_result(scalars_all=[mock_sw]),
    ]
    resp = await get_pending_review(db, current_user, page=1, page_size=20)
    assert resp.success is True
    assert resp.pagination.total_items == 1
    
    db.execute.side_effect = None
    
    # Test get expired
    mock_sw_expired = MagicMock(spec=StandardWork)
    mock_sw_expired.id = 2
    mock_sw_expired.document_number = "SW-002"
    mock_sw_expired.title = "Expired Doc"
    mock_sw_expired.description = None
    mock_sw_expired.version = 1
    mock_sw_expired.revision_code = "A"
    mock_sw_expired.document_type = StandardWorkType.WORK_INSTRUCTION
    mock_sw_expired.status = StandardWorkStatus.APPROVED
    mock_sw_expired.product_id = None
    mock_sw_expired.station_id = None
    mock_sw_expired.content_json = None
    mock_sw_expired.effective_date = None
    mock_sw_expired.expiration_date = today - timedelta(days=30)
    mock_sw_expired.review_date = None
    mock_sw_expired.submitted_by_id = None
    mock_sw_expired.submitted_at = None
    mock_sw_expired.approved_by_id = None
    mock_sw_expired.approved_at = None
    mock_sw_expired.approval_notes = None
    mock_sw_expired.change_summary = None
    mock_sw_expired.previous_version_id = None
    mock_sw_expired.requires_training = True
    mock_sw_expired.training_duration_minutes = 30
    mock_sw_expired.created_at = now
    mock_sw_expired.updated_at = now
    mock_sw_expired.is_deleted = False
    mock_sw_expired.full_document_id = "SW-002-RevA"
    mock_sw_expired.is_current = True
    mock_sw_expired.is_expired = True
    mock_sw_expired.needs_review = False
    mock_sw_expired.step_count = 0
    
    db.execute.side_effect = [
        make_result(scalar_one=1),
        make_result(scalars_all=[mock_sw_expired]),
    ]
    resp = await get_expired(db, current_user, page=1, page_size=20)
    assert resp.success is True
    assert resp.pagination.total_items == 1


# =============================================================================
# Edge Case Tests
# =============================================================================


@pytest.mark.asyncio
async def test_standard_work_edge_cases(db, current_user):
    """Test edge cases and error conditions."""
    now = datetime.utcnow()
    
    # Test submit not found
    db.execute.return_value = make_result(scalar_one_or_none=None)
    with pytest.raises(NotFoundError):
        await submit_for_approval(1, StandardWorkSubmit(), db, current_user)
    
    # Test approve not found
    db.execute.return_value = make_result(scalar_one_or_none=None)
    with pytest.raises(NotFoundError):
        await approve_standard_work(1, StandardWorkApprove(), db, current_user)
    
    # Test reject not found
    db.execute.return_value = make_result(scalar_one_or_none=None)
    with pytest.raises(NotFoundError):
        await reject_standard_work(1, StandardWorkReject(rejection_notes="N/A"), db, current_user)
    
    # Test create revision not found
    db.execute.return_value = make_result(scalar_one_or_none=None)
    with pytest.raises(NotFoundError):
        await create_revision(1, StandardWorkRevise(), db, current_user)
    
    # Test mark obsolete not found
    db.execute.return_value = make_result(scalar_one_or_none=None)
    with pytest.raises(NotFoundError):
        await mark_obsolete(1, db, current_user)


@pytest.mark.asyncio
async def test_standard_work_document_types(db, current_user):
    """Test all document types can be created."""
    now = datetime.utcnow()
    
    for doc_type in StandardWorkType:
        sw = None
        
        def capture_add(obj):
            nonlocal sw
            sw = obj
            obj.id = 1
            obj.document_number = f"SW-{doc_type.value}"
            obj.title = f"Test {doc_type.value}"
            obj.description = None
            obj.version = 1
            obj.revision_code = "A"
            obj.document_type = doc_type
            obj.status = StandardWorkStatus.DRAFT
            obj.product_id = None
            obj.station_id = None
            obj.content_json = None
            obj.effective_date = None
            obj.expiration_date = None
            obj.review_date = None
            obj.submitted_by_id = None
            obj.submitted_at = None
            obj.approved_by_id = None
            obj.approved_at = None
            obj.approval_notes = None
            obj.change_summary = None
            obj.previous_version_id = None
            obj.requires_training = True
            obj.training_duration_minutes = 30
            obj.created_at = now
            obj.updated_at = now
            obj.deleted_at = None  # is_deleted is computed from this
            
        db.add.side_effect = capture_add
        db.execute.return_value = make_result(scalar_one_or_none=None)
        
        resp = await create_standard_work(
            StandardWorkCreate(
                document_number=f"SW-{doc_type.value}",
                title=f"Test {doc_type.value}",
                document_type=doc_type,
            ),
            db,
            current_user,
        )
        assert resp.success is True
        assert resp.data.document_type == doc_type
        
        db.add.side_effect = None
