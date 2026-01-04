"""
Tests for Sensei OS API Schemas

Comprehensive tests for all API request/response schemas.
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from sensei.api.schemas import (
    APIResponse,
    PaginatedResponse,
    PaginationMeta,
    ErrorResponse,
    ValidationErrorDetail,
    ValidationErrorResponse,
    IDRequest,
    IDsRequest,
    BulkDeleteRequest,
    SortOrder,
    SearchRequest,
    FilterOperator,
    FilterRequest,
    AuditInfo,
    EntityMeta,
    StatusUpdateRequest,
    ArchiveRequest,
    AttachmentInfo,
    AttachmentUploadResponse,
    HealthStatus,
    ServiceStatus,
    PermissionInfo,
    AccessControlResponse,
    BulkOperationResult,
    ExportRequest,
    ExportResponse,
    ImportResult,
    ImportPreviewRow,
    ImportPreviewResponse,
    WebhookEvent,
    success_response,
    error_response,
    paginated_response,
)


class TestAPIResponse:
    """Tests for APIResponse model."""
    
    def test_success_response_with_data(self):
        """Test creating success response with data."""
        data = {"id": "123", "name": "Test"}
        response = APIResponse(success=True, data=data)
        
        assert response.success is True
        assert response.data == data
        assert response.message is None
        assert response.errors is None
    
    def test_success_response_with_message(self):
        """Test creating success response with message."""
        response = APIResponse(success=True, message="Operation completed")
        
        assert response.success is True
        assert response.message == "Operation completed"
        assert response.data is None
    
    def test_failure_response_with_errors(self):
        """Test creating failure response with errors."""
        response = APIResponse(
            success=False,
            message="Validation failed",
            errors=["Field required", "Invalid format"],
        )
        
        assert response.success is False
        assert response.message == "Validation failed"
        assert len(response.errors) == 2
    
    def test_default_success_true(self):
        """Test that success defaults to True."""
        response = APIResponse()
        assert response.success is True


class TestPaginationMeta:
    """Tests for PaginationMeta model."""
    
    def test_from_pagination(self):
        """Test creating pagination meta from parameters."""
        meta = PaginationMeta.from_pagination(
            page=2,
            page_size=10,
            total_items=35,
        )
        
        assert meta.page == 2
        assert meta.page_size == 10
        assert meta.total_items == 35
        assert meta.total_pages == 4
        assert meta.has_next is True
        assert meta.has_prev is True
    
    def test_first_page(self):
        """Test pagination on first page."""
        meta = PaginationMeta.from_pagination(
            page=1,
            page_size=10,
            total_items=35,
        )
        
        assert meta.has_prev is False
        assert meta.has_next is True
    
    def test_last_page(self):
        """Test pagination on last page."""
        meta = PaginationMeta.from_pagination(
            page=4,
            page_size=10,
            total_items=35,
        )
        
        assert meta.has_prev is True
        assert meta.has_next is False
    
    def test_single_page(self):
        """Test pagination with single page."""
        meta = PaginationMeta.from_pagination(
            page=1,
            page_size=10,
            total_items=5,
        )
        
        assert meta.total_pages == 1
        assert meta.has_prev is False
        assert meta.has_next is False
    
    def test_empty_result(self):
        """Test pagination with empty result."""
        meta = PaginationMeta.from_pagination(
            page=1,
            page_size=10,
            total_items=0,
        )
        
        assert meta.total_pages == 0
        assert meta.total_items == 0
        assert meta.has_prev is False
        assert meta.has_next is False
    
    def test_exact_pages(self):
        """Test pagination with exactly divisible items."""
        meta = PaginationMeta.from_pagination(
            page=1,
            page_size=10,
            total_items=30,
        )
        
        assert meta.total_pages == 3


class TestPaginatedResponse:
    """Tests for PaginatedResponse model."""
    
    def test_paginated_response(self):
        """Test creating paginated response."""
        response = PaginatedResponse(
            data=[{"id": 1}, {"id": 2}],
            pagination=PaginationMeta.from_pagination(
                page=1,
                page_size=10,
                total_items=2,
            ),
        )
        
        assert response.success is True
        assert len(response.data) == 2
        assert response.pagination.total_items == 2


class TestErrorResponse:
    """Tests for ErrorResponse model."""
    
    def test_basic_error(self):
        """Test basic error response."""
        response = ErrorResponse(message="Something went wrong")
        
        assert response.success is False
        assert response.message == "Something went wrong"
    
    def test_error_with_code_and_details(self):
        """Test error response with code and details."""
        response = ErrorResponse(
            message="Not found",
            error_code="NOT_FOUND",
            details={"resource": "User", "id": "123"},
        )
        
        assert response.error_code == "NOT_FOUND"
        assert response.details["resource"] == "User"


class TestValidationErrorResponse:
    """Tests for ValidationErrorResponse model."""
    
    def test_validation_errors(self):
        """Test validation error response."""
        response = ValidationErrorResponse(
            errors=[
                ValidationErrorDetail(field="email", message="Invalid email", type="value_error"),
                ValidationErrorDetail(field="password", message="Too short", type="value_error"),
            ],
        )
        
        assert response.success is False
        assert response.message == "Validation error"
        assert len(response.errors) == 2
        assert response.errors[0].field == "email"


class TestIDRequests:
    """Tests for ID request models."""
    
    def test_id_request(self):
        """Test single ID request."""
        uid = uuid4()
        request = IDRequest(id=uid)
        assert request.id == uid
    
    def test_ids_request(self):
        """Test multiple IDs request."""
        ids = [uuid4(), uuid4(), uuid4()]
        request = IDsRequest(ids=ids)
        assert len(request.ids) == 3
    
    def test_bulk_delete_request(self):
        """Test bulk delete request."""
        ids = [uuid4(), uuid4()]
        request = BulkDeleteRequest(ids=ids)
        
        assert len(request.ids) == 2
        assert request.force is False
    
    def test_bulk_delete_request_with_force(self):
        """Test bulk delete request with force flag."""
        request = BulkDeleteRequest(ids=[uuid4()], force=True)
        assert request.force is True
    
    def test_bulk_delete_request_empty_fails(self):
        """Test bulk delete request with empty list fails."""
        with pytest.raises(ValueError):
            BulkDeleteRequest(ids=[])


class TestSortOrder:
    """Tests for SortOrder model."""
    
    def test_default_direction(self):
        """Test default sort direction is asc."""
        sort = SortOrder(field="name")
        assert sort.direction == "asc"
    
    def test_desc_direction(self):
        """Test desc sort direction."""
        sort = SortOrder(field="created_at", direction="desc")
        assert sort.direction == "desc"
    
    def test_invalid_direction_fails(self):
        """Test invalid sort direction fails validation."""
        with pytest.raises(ValueError):
            SortOrder(field="name", direction="invalid")


class TestSearchRequest:
    """Tests for SearchRequest model."""
    
    def test_basic_search(self):
        """Test basic search request."""
        request = SearchRequest(query="test query")
        assert request.query == "test query"
        assert request.fields is None
    
    def test_search_with_fields(self):
        """Test search request with specific fields."""
        request = SearchRequest(
            query="test",
            fields=["name", "description"],
        )
        assert len(request.fields) == 2
    
    def test_empty_query_fails(self):
        """Test empty query fails validation."""
        with pytest.raises(ValueError):
            SearchRequest(query="")


class TestFilterOperator:
    """Tests for FilterOperator model."""
    
    def test_default_operator(self):
        """Test default operator is eq."""
        filter_op = FilterOperator(field="status", value="active")
        assert filter_op.operator == "eq"
    
    def test_custom_operator(self):
        """Test custom operator."""
        filter_op = FilterOperator(
            field="count",
            operator="gte",
            value=10,
        )
        assert filter_op.operator == "gte"
    
    def test_list_value(self):
        """Test filter with list value."""
        filter_op = FilterOperator(
            field="status",
            operator="in",
            value=["active", "pending"],
        )
        assert isinstance(filter_op.value, list)


class TestFilterRequest:
    """Tests for FilterRequest model."""
    
    def test_empty_filter(self):
        """Test empty filter request."""
        request = FilterRequest()
        assert request.filters == []
        assert request.search is None
        assert request.sort is None
    
    def test_full_filter_request(self):
        """Test full filter request."""
        request = FilterRequest(
            filters=[FilterOperator(field="status", value="active")],
            search="test",
            sort=[SortOrder(field="name", direction="asc")],
        )
        assert len(request.filters) == 1
        assert request.search == "test"
        assert len(request.sort) == 1


class TestAuditInfo:
    """Tests for AuditInfo model."""
    
    def test_audit_info(self):
        """Test audit info creation."""
        now = datetime.now(timezone.utc)
        user_id = uuid4()
        
        info = AuditInfo(
            created_at=now,
            created_by=user_id,
        )
        
        assert info.created_at == now
        assert info.created_by == user_id
        assert info.updated_at is None
        assert info.deleted_at is None


class TestEntityMeta:
    """Tests for EntityMeta model."""
    
    def test_entity_meta(self):
        """Test entity meta creation."""
        entity_id = uuid4()
        now = datetime.now(timezone.utc)
        
        meta = EntityMeta(id=entity_id, created_at=now)
        
        assert meta.id == entity_id
        assert meta.created_at == now


class TestStatusUpdateRequest:
    """Tests for StatusUpdateRequest model."""
    
    def test_status_update(self):
        """Test status update request."""
        request = StatusUpdateRequest(status="active")
        assert request.status == "active"
        assert request.reason is None
    
    def test_status_update_with_reason(self):
        """Test status update with reason."""
        request = StatusUpdateRequest(
            status="inactive",
            reason="Account suspended due to policy violation",
        )
        assert request.reason is not None


class TestArchiveRequest:
    """Tests for ArchiveRequest model."""
    
    def test_archive(self):
        """Test archive request."""
        request = ArchiveRequest(archived=True)
        assert request.archived is True
    
    def test_unarchive(self):
        """Test unarchive request."""
        request = ArchiveRequest(archived=False)
        assert request.archived is False


class TestAttachmentInfo:
    """Tests for AttachmentInfo model."""
    
    def test_attachment_info(self):
        """Test attachment info creation."""
        attachment_id = uuid4()
        now = datetime.now(timezone.utc)
        
        info = AttachmentInfo(
            id=attachment_id,
            filename="document.pdf",
            content_type="application/pdf",
            size_bytes=1024,
            uploaded_at=now,
        )
        
        assert info.filename == "document.pdf"
        assert info.size_bytes == 1024


class TestHealthStatus:
    """Tests for HealthStatus model."""
    
    def test_healthy_status(self):
        """Test healthy status."""
        status = HealthStatus(
            status="healthy",
            version="1.0.0",
            environment="development",
            services={"database": True, "redis": True},
        )
        
        assert status.status == "healthy"
        assert status.services["database"] is True


class TestServiceStatus:
    """Tests for ServiceStatus model."""
    
    def test_service_status(self):
        """Test service status."""
        status = ServiceStatus(
            name="database",
            healthy=True,
            latency_ms=5.2,
        )
        
        assert status.healthy is True
        assert status.latency_ms == 5.2


class TestPermissionInfo:
    """Tests for PermissionInfo model."""
    
    def test_default_permissions(self):
        """Test default permissions."""
        info = PermissionInfo()
        
        assert info.can_view is True
        assert info.can_edit is False
        assert info.can_delete is False
        assert info.can_approve is False
    
    def test_full_permissions(self):
        """Test full permissions."""
        info = PermissionInfo(
            can_view=True,
            can_edit=True,
            can_delete=True,
            can_approve=True,
            can_export=True,
        )
        
        assert all([
            info.can_view,
            info.can_edit,
            info.can_delete,
            info.can_approve,
            info.can_export,
        ])


class TestBulkOperationResult:
    """Tests for BulkOperationResult model."""
    
    def test_successful_bulk_operation(self):
        """Test successful bulk operation."""
        result = BulkOperationResult(
            total=10,
            succeeded=10,
            failed=0,
        )
        
        assert result.success is True
        assert result.errors is None
    
    def test_partial_bulk_operation(self):
        """Test partial bulk operation."""
        result = BulkOperationResult(
            success=False,
            total=10,
            succeeded=7,
            failed=3,
            errors=[{"id": "123", "error": "Invalid state"}],
        )
        
        assert result.success is False
        assert result.failed == 3


class TestExportRequest:
    """Tests for ExportRequest model."""
    
    def test_default_export(self):
        """Test default export request."""
        request = ExportRequest()
        assert request.format == "csv"
        assert request.fields is None
    
    def test_pdf_export(self):
        """Test PDF export request."""
        request = ExportRequest(format="pdf")
        assert request.format == "pdf"
    
    def test_invalid_format_fails(self):
        """Test invalid export format fails."""
        with pytest.raises(ValueError):
            ExportRequest(format="invalid")


class TestExportResponse:
    """Tests for ExportResponse model."""
    
    def test_export_response(self):
        """Test export response."""
        response = ExportResponse(
            download_url="https://example.com/file.csv",
            filename="export.csv",
            format="csv",
            record_count=100,
            expires_at=datetime.now(timezone.utc),
        )
        
        assert response.success is True
        assert response.record_count == 100


class TestImportResult:
    """Tests for ImportResult model."""
    
    def test_successful_import(self):
        """Test successful import."""
        result = ImportResult(
            total_rows=100,
            imported=100,
            skipped=0,
            failed=0,
        )
        
        assert result.success is True
        assert result.imported == 100
    
    def test_partial_import(self):
        """Test partial import with errors."""
        result = ImportResult(
            success=False,
            total_rows=100,
            imported=95,
            skipped=3,
            failed=2,
            errors=[{"row": 5, "error": "Invalid format"}],
        )
        
        assert result.failed == 2


class TestImportPreview:
    """Tests for import preview models."""
    
    def test_preview_row_valid(self):
        """Test valid preview row."""
        row = ImportPreviewRow(
            row_number=1,
            data={"name": "Test", "email": "test@example.com"},
            valid=True,
        )
        
        assert row.valid is True
        assert row.errors is None
    
    def test_preview_row_invalid(self):
        """Test invalid preview row."""
        row = ImportPreviewRow(
            row_number=2,
            data={"name": "", "email": "invalid"},
            valid=False,
            errors=["Name required", "Invalid email"],
        )
        
        assert row.valid is False
        assert len(row.errors) == 2
    
    def test_preview_response(self):
        """Test import preview response."""
        response = ImportPreviewResponse(
            total_rows=100,
            valid_rows=95,
            invalid_rows=5,
            preview=[
                ImportPreviewRow(row_number=1, data={}, valid=True),
            ],
            column_mapping={"col1": "name", "col2": "email"},
        )
        
        assert response.valid_rows == 95


class TestWebhookEvent:
    """Tests for WebhookEvent model."""
    
    def test_webhook_event(self):
        """Test webhook event creation."""
        object_id = uuid4()
        actor_id = uuid4()
        
        event = WebhookEvent(
            event_type="user.created",
            timestamp=datetime.now(timezone.utc),
            object_type="User",
            object_id=object_id,
            action="create",
            actor_id=actor_id,
            data={"name": "John Doe"},
        )
        
        assert event.event_type == "user.created"
        assert event.action == "create"
        assert event.data["name"] == "John Doe"


class TestHelperFunctions:
    """Tests for helper functions."""
    
    def test_success_response_helper(self):
        """Test success_response helper."""
        response = success_response(
            data={"id": 1},
            message="Created",
        )
        
        assert response.success is True
        assert response.data == {"id": 1}
        assert response.message == "Created"
    
    def test_error_response_helper(self):
        """Test error_response helper."""
        response = error_response(
            message="Not found",
            error_code="NOT_FOUND",
        )
        
        assert response.success is False
        assert response.message == "Not found"
        assert response.error_code == "NOT_FOUND"
    
    def test_paginated_response_helper(self):
        """Test paginated_response helper."""
        response = paginated_response(
            data=[1, 2, 3],
            page=1,
            page_size=10,
            total_items=3,
        )
        
        assert response.success is True
        assert len(response.data) == 3
        assert response.pagination.total_items == 3
