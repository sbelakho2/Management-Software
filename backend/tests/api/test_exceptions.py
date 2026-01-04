"""
Tests for Sensei OS API Exceptions

Comprehensive tests for custom exceptions and exception handlers.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from sensei.api.exceptions import (
    SenseiException,
    NotFoundError,
    ConflictError,
    BadRequestError,
    UnauthorizedError,
    ForbiddenError,
    UnprocessableEntityError,
    RateLimitError,
    ServiceUnavailableError,
    BusinessRuleViolationError,
    StateTransitionError,
    ApprovalRequiredError,
    FileOperationError,
    ExternalServiceError,
    register_exception_handlers,
    sensei_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    integrity_error_handler,
    generic_exception_handler,
)


# =============================================================================
# Custom Exception Tests
# =============================================================================


class TestSenseiException:
    """Tests for base SenseiException."""
    
    def test_basic_exception(self):
        """Test basic exception creation."""
        exc = SenseiException(message="Something went wrong")
        
        assert exc.message == "Something went wrong"
        assert exc.status_code == 500
        assert exc.error_code is None
        assert exc.details is None
        assert str(exc) == "Something went wrong"
    
    def test_exception_with_all_fields(self):
        """Test exception with all fields."""
        exc = SenseiException(
            message="Error occurred",
            status_code=400,
            error_code="BAD_REQUEST",
            details={"field": "value"},
        )
        
        assert exc.status_code == 400
        assert exc.error_code == "BAD_REQUEST"
        assert exc.details == {"field": "value"}


class TestNotFoundError:
    """Tests for NotFoundError."""
    
    def test_basic_not_found(self):
        """Test basic not found error."""
        exc = NotFoundError(resource="User")
        
        assert exc.message == "User not found"
        assert exc.status_code == 404
        assert exc.error_code == "NOT_FOUND"
    
    def test_not_found_with_identifier(self):
        """Test not found error with identifier."""
        exc = NotFoundError(resource="User", identifier="123")
        
        assert exc.message == "User with ID '123' not found"
    
    def test_not_found_with_details(self):
        """Test not found error with details."""
        exc = NotFoundError(
            resource="Account",
            identifier="456",
            details={"reason": "Deleted"},
        )
        
        assert exc.details["reason"] == "Deleted"


class TestConflictError:
    """Tests for ConflictError."""
    
    def test_conflict_error(self):
        """Test conflict error."""
        exc = ConflictError(message="Resource already exists")
        
        assert exc.message == "Resource already exists"
        assert exc.status_code == 409
        assert exc.error_code == "CONFLICT"


class TestBadRequestError:
    """Tests for BadRequestError."""
    
    def test_bad_request_error(self):
        """Test bad request error."""
        exc = BadRequestError(message="Invalid input")
        
        assert exc.message == "Invalid input"
        assert exc.status_code == 400
        assert exc.error_code == "BAD_REQUEST"


class TestUnauthorizedError:
    """Tests for UnauthorizedError."""
    
    def test_default_message(self):
        """Test unauthorized error with default message."""
        exc = UnauthorizedError()
        
        assert exc.message == "Authentication required"
        assert exc.status_code == 401
        assert exc.error_code == "UNAUTHORIZED"
    
    def test_custom_message(self):
        """Test unauthorized error with custom message."""
        exc = UnauthorizedError(message="Token expired")
        assert exc.message == "Token expired"


class TestForbiddenError:
    """Tests for ForbiddenError."""
    
    def test_default_message(self):
        """Test forbidden error with default message."""
        exc = ForbiddenError()
        
        assert exc.message == "Access denied"
        assert exc.status_code == 403
        assert exc.error_code == "FORBIDDEN"
    
    def test_with_permission(self):
        """Test forbidden error with required permission."""
        exc = ForbiddenError(required_permission="admin:write")
        
        assert "admin:write" in exc.message


class TestUnprocessableEntityError:
    """Tests for UnprocessableEntityError."""
    
    def test_unprocessable_entity_error(self):
        """Test unprocessable entity error."""
        exc = UnprocessableEntityError(message="Cannot process request")
        
        assert exc.status_code == 422
        assert exc.error_code == "UNPROCESSABLE_ENTITY"


class TestRateLimitError:
    """Tests for RateLimitError."""
    
    def test_rate_limit_error(self):
        """Test rate limit error."""
        exc = RateLimitError(retry_after=60)
        
        assert exc.status_code == 429
        assert exc.error_code == "RATE_LIMIT_EXCEEDED"
        assert exc.retry_after == 60
        assert "60 seconds" in exc.message
        assert exc.details["retry_after"] == 60


class TestServiceUnavailableError:
    """Tests for ServiceUnavailableError."""
    
    def test_default_message(self):
        """Test service unavailable with default message."""
        exc = ServiceUnavailableError()
        
        assert exc.status_code == 503
        assert exc.error_code == "SERVICE_UNAVAILABLE"
    
    def test_custom_message(self):
        """Test service unavailable with custom message."""
        exc = ServiceUnavailableError(message="Database offline")
        assert exc.message == "Database offline"


class TestBusinessRuleViolationError:
    """Tests for BusinessRuleViolationError."""
    
    def test_business_rule_violation(self):
        """Test business rule violation error."""
        exc = BusinessRuleViolationError(
            rule="MIN_ORDER_QUANTITY",
            message="Order quantity must be at least 10",
        )
        
        assert exc.status_code == 422
        assert "MIN_ORDER_QUANTITY" in exc.error_code
        assert exc.message == "Order quantity must be at least 10"


class TestStateTransitionError:
    """Tests for StateTransitionError."""
    
    def test_basic_transition_error(self):
        """Test basic state transition error."""
        exc = StateTransitionError(
            from_state="draft",
            to_state="completed",
            entity_type="WorkOrder",
        )
        
        assert "draft" in exc.message
        assert "completed" in exc.message
        assert "WorkOrder" in exc.message
        assert exc.status_code == 422
    
    def test_with_allowed_transitions(self):
        """Test state transition error with allowed transitions."""
        exc = StateTransitionError(
            from_state="draft",
            to_state="completed",
            entity_type="Quote",
            allowed_transitions=["in_progress", "cancelled"],
        )
        
        assert "in_progress" in exc.message
        assert exc.details["allowed_transitions"] == ["in_progress", "cancelled"]


class TestApprovalRequiredError:
    """Tests for ApprovalRequiredError."""
    
    def test_approval_required(self):
        """Test approval required error."""
        exc = ApprovalRequiredError(
            action="release_quote",
            approvers=["manager", "finance"],
        )
        
        assert exc.status_code == 403
        assert exc.error_code == "APPROVAL_REQUIRED"
        assert exc.details["action"] == "release_quote"
        assert "manager" in exc.details["approvers"]


class TestFileOperationError:
    """Tests for FileOperationError."""
    
    def test_file_operation_error(self):
        """Test file operation error."""
        exc = FileOperationError(
            operation="upload",
            message="File too large",
        )
        
        assert "upload" in exc.message.lower()
        assert "File too large" in exc.message
        assert "UPLOAD" in exc.error_code


class TestExternalServiceError:
    """Tests for ExternalServiceError."""
    
    def test_external_service_error(self):
        """Test external service error."""
        exc = ExternalServiceError(
            service="payment_gateway",
            message="Connection timeout",
        )
        
        assert exc.status_code == 502
        assert "payment_gateway" in exc.message
        assert "PAYMENT_GATEWAY" in exc.error_code


# =============================================================================
# Exception Handler Tests
# =============================================================================


class TestExceptionHandlerIntegration:
    """Integration tests for exception handlers."""
    
    @pytest.fixture
    def app(self):
        """Create test FastAPI application with exception handlers."""
        app = FastAPI()
        register_exception_handlers(app)
        
        @app.get("/not-found")
        async def not_found():
            raise NotFoundError(resource="User", identifier="123")
        
        @app.get("/conflict")
        async def conflict():
            raise ConflictError(message="Duplicate entry")
        
        @app.get("/rate-limit")
        async def rate_limit():
            raise RateLimitError(retry_after=120)
        
        @app.get("/business-rule")
        async def business_rule():
            raise BusinessRuleViolationError(
                rule="MIN_QUANTITY",
                message="Minimum quantity is 10",
            )
        
        @app.get("/state-transition")
        async def state_transition():
            raise StateTransitionError(
                from_state="draft",
                to_state="completed",
                entity_type="Order",
                allowed_transitions=["submitted", "cancelled"],
            )
        
        @app.get("/generic-error")
        async def generic_error():
            raise ValueError("Unexpected error")
        
        return app
    
    @pytest.mark.asyncio
    async def test_not_found_handler(self, app):
        """Test NotFoundError handler."""
        transport = ASGITransport(app=app)
        
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/not-found")
        
        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False
        assert "User with ID '123' not found" in data["message"]
        assert data["error_code"] == "NOT_FOUND"
    
    @pytest.mark.asyncio
    async def test_conflict_handler(self, app):
        """Test ConflictError handler."""
        transport = ASGITransport(app=app)
        
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/conflict")
        
        assert response.status_code == 409
        data = response.json()
        assert data["error_code"] == "CONFLICT"
    
    @pytest.mark.asyncio
    async def test_rate_limit_handler(self, app):
        """Test RateLimitError handler with Retry-After header."""
        transport = ASGITransport(app=app)
        
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/rate-limit")
        
        assert response.status_code == 429
        assert response.headers.get("Retry-After") == "120"
    
    @pytest.mark.asyncio
    async def test_business_rule_handler(self, app):
        """Test BusinessRuleViolationError handler."""
        transport = ASGITransport(app=app)
        
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/business-rule")
        
        assert response.status_code == 422
        data = response.json()
        assert "MIN_QUANTITY" in data["error_code"]
    
    @pytest.mark.asyncio
    async def test_state_transition_handler(self, app):
        """Test StateTransitionError handler."""
        transport = ASGITransport(app=app)
        
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/state-transition")
        
        assert response.status_code == 422
        data = response.json()
        assert "details" in data
        assert data["details"]["from_state"] == "draft"
        assert data["details"]["allowed_transitions"] == ["submitted", "cancelled"]
    
    @pytest.mark.asyncio
    async def test_generic_error_handler(self, app):
        """Test generic exception handler."""
        # Note: FastAPI's generic exception handlers work differently in tests
        # because ServerErrorMiddleware catches exceptions before handlers.
        # This test verifies our handler is registered but in real usage
        # the middleware handles generic exceptions.
        # We test the handler function directly instead.
        from sensei.api.exceptions import generic_exception_handler
        from starlette.requests import Request
        from starlette.testclient import TestClient
        
        # Test the handler function directly
        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/test"
        mock_request.method = "GET"
        
        response = await generic_exception_handler(
            mock_request,
            ValueError("Unexpected error"),
        )
        
        assert response.status_code == 500
        import json
        data = json.loads(response.body)
        assert data["success"] is False
        assert data["error_code"] == "INTERNAL_ERROR"


class TestValidationExceptionHandler:
    """Tests for validation exception handler."""
    
    @pytest.fixture
    def app(self):
        """Create test app with validation endpoint."""
        from pydantic import BaseModel, Field
        
        app = FastAPI()
        register_exception_handlers(app)
        
        class CreateRequest(BaseModel):
            name: str = Field(..., min_length=1)
            email: str
            age: int = Field(..., ge=0)
        
        @app.post("/create")
        async def create(request: CreateRequest):
            return {"status": "ok"}
        
        return app
    
    @pytest.mark.asyncio
    async def test_validation_error_response(self, app):
        """Test validation error produces proper response."""
        transport = ASGITransport(app=app)
        
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/create",
                json={"name": "", "age": -1},  # Missing email, invalid name and age
            )
        
        assert response.status_code == 422
        data = response.json()
        assert data["success"] is False
        assert "errors" in data
        assert len(data["errors"]) > 0
        
        # Check error structure
        error = data["errors"][0]
        assert "field" in error
        assert "message" in error
        assert "type" in error


class TestIntegrityErrorHandler:
    """Tests for database integrity error handler."""
    
    @pytest.fixture
    def app(self):
        """Create test app with integrity error simulation."""
        app = FastAPI()
        register_exception_handlers(app)
        
        @app.get("/duplicate")
        async def duplicate():
            exc = IntegrityError(
                "INSERT",
                {},
                Exception("duplicate key value violates unique constraint"),
            )
            raise exc
        
        @app.get("/foreign-key")
        async def foreign_key():
            exc = IntegrityError(
                "INSERT",
                {},
                Exception("foreign key constraint violation"),
            )
            raise exc
        
        @app.get("/not-null")
        async def not_null():
            exc = IntegrityError(
                "INSERT",
                {},
                Exception("null value in column violates not null constraint"),
            )
            raise exc
        
        return app
    
    @pytest.mark.asyncio
    async def test_duplicate_key_error(self, app):
        """Test duplicate key integrity error."""
        transport = ASGITransport(app=app)
        
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/duplicate")
        
        assert response.status_code == 409
        data = response.json()
        assert data["error_code"] == "DUPLICATE_ENTRY"
    
    @pytest.mark.asyncio
    async def test_foreign_key_error(self, app):
        """Test foreign key integrity error."""
        transport = ASGITransport(app=app)
        
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/foreign-key")
        
        assert response.status_code == 409
        data = response.json()
        assert data["error_code"] == "FOREIGN_KEY_VIOLATION"
    
    @pytest.mark.asyncio
    async def test_not_null_error(self, app):
        """Test not null integrity error."""
        transport = ASGITransport(app=app)
        
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/not-null")
        
        assert response.status_code == 409
        data = response.json()
        assert data["error_code"] == "NOT_NULL_VIOLATION"


class TestHTTPExceptionHandler:
    """Tests for HTTP exception handler."""
    
    @pytest.fixture
    def app(self):
        """Create test app with HTTP exceptions."""
        from fastapi import HTTPException
        
        app = FastAPI()
        register_exception_handlers(app)
        
        @app.get("/http-error")
        async def http_error():
            raise HTTPException(status_code=400, detail="Bad request")
        
        @app.get("/http-error-custom")
        async def http_error_custom():
            raise HTTPException(
                status_code=418,
                detail="I'm a teapot",
            )
        
        return app
    
    @pytest.mark.asyncio
    async def test_http_exception(self, app):
        """Test HTTP exception handling."""
        transport = ASGITransport(app=app)
        
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/http-error")
        
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert data["message"] == "Bad request"
    
    @pytest.mark.asyncio
    async def test_custom_http_exception(self, app):
        """Test custom HTTP status code."""
        transport = ASGITransport(app=app)
        
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/http-error-custom")
        
        assert response.status_code == 418
        data = response.json()
        assert data["error_code"] == "HTTP_418"
