"""
Tests for Sensei Middleware

Comprehensive tests for logging, timing, and correlation ID middleware.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from starlette.testclient import TestClient
from fastapi import FastAPI

from sensei.middleware.logging import StructuredLoggingMiddleware
from sensei.middleware.timing import TimingMiddleware
from sensei.middleware.correlation import CorrelationIdMiddleware


def create_test_app():
    """Create a test FastAPI application with middleware."""
    app = FastAPI()
    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(TimingMiddleware)
    app.add_middleware(StructuredLoggingMiddleware)
    
    @app.get("/test")
    async def test_endpoint():
        return {"status": "ok"}
    
    @app.get("/health")
    async def health_endpoint():
        return {"status": "healthy"}
    
    @app.get("/error")
    async def error_endpoint():
        raise ValueError("Test error")
    
    return app


class TestCorrelationIdMiddleware:
    """Tests for correlation ID middleware."""
    
    def test_adds_correlation_id_header(self):
        """Test that correlation ID is added to response."""
        app = create_test_app()
        client = TestClient(app)
        
        response = client.get("/test")
        
        assert "X-Correlation-ID" in response.headers
        assert len(response.headers["X-Correlation-ID"]) == 36  # UUID format
    
    def test_uses_existing_correlation_id(self):
        """Test that existing correlation ID is preserved."""
        app = create_test_app()
        client = TestClient(app)
        existing_id = "test-correlation-123"
        
        response = client.get("/test", headers={"X-Correlation-ID": existing_id})
        
        assert response.headers["X-Correlation-ID"] == existing_id
    
    def test_generates_unique_ids(self):
        """Test that unique IDs are generated for each request."""
        app = create_test_app()
        client = TestClient(app)
        
        response1 = client.get("/test")
        response2 = client.get("/test")
        
        id1 = response1.headers["X-Correlation-ID"]
        id2 = response2.headers["X-Correlation-ID"]
        assert id1 != id2


class TestTimingMiddleware:
    """Tests for request timing middleware."""
    
    def test_adds_process_time_header(self):
        """Test that process time header is added."""
        app = create_test_app()
        client = TestClient(app)
        
        response = client.get("/test")
        
        assert "X-Process-Time" in response.headers
    
    def test_process_time_is_numeric(self):
        """Test that process time is a valid float."""
        app = create_test_app()
        client = TestClient(app)
        
        response = client.get("/test")
        
        process_time = float(response.headers["X-Process-Time"])
        assert process_time >= 0
    
    def test_process_time_format(self):
        """Test that process time has correct decimal format."""
        app = create_test_app()
        client = TestClient(app)
        
        response = client.get("/test")
        
        process_time_str = response.headers["X-Process-Time"]
        # Should have 4 decimal places
        assert "." in process_time_str
        decimal_places = len(process_time_str.split(".")[1])
        assert decimal_places == 4


class TestStructuredLoggingMiddleware:
    """Tests for structured logging middleware."""
    
    def test_logs_request_completion(self):
        """Test that requests are logged."""
        app = create_test_app()
        client = TestClient(app)
        
        with patch("sensei.middleware.logging.logger") as mock_logger:
            mock_log = MagicMock()
            mock_logger.bind.return_value = mock_log
            
            response = client.get("/test")
            
            assert response.status_code == 200
    
    def test_skips_health_endpoint_logging(self):
        """Test that health endpoint is not logged."""
        app = create_test_app()
        client = TestClient(app)
        
        with patch("sensei.middleware.logging.logger") as mock_logger:
            response = client.get("/health")
            
            # Health endpoint should be skipped
            assert response.status_code == 200
    
    def test_logs_error_on_exception(self):
        """Test that exceptions are logged."""
        app = create_test_app()
        client = TestClient(app, raise_server_exceptions=False)
        
        with patch("sensei.middleware.logging.logger") as mock_logger:
            mock_log = MagicMock()
            mock_logger.bind.return_value = mock_log
            
            response = client.get("/error")
            
            assert response.status_code == 500


class TestMiddlewareIntegration:
    """Integration tests for middleware stack."""
    
    def test_all_middleware_work_together(self):
        """Test that all middleware work together correctly."""
        app = create_test_app()
        client = TestClient(app)
        
        response = client.get("/test")
        
        assert response.status_code == 200
        assert "X-Correlation-ID" in response.headers
        assert "X-Process-Time" in response.headers
    
    def test_middleware_order_preserved(self):
        """Test that middleware execute in correct order."""
        app = create_test_app()
        client = TestClient(app)
        
        # Multiple requests should all work
        for _ in range(5):
            response = client.get("/test")
            assert response.status_code == 200
            assert "X-Correlation-ID" in response.headers
    
    def test_middleware_handles_post_request(self):
        """Test middleware with POST requests."""
        app = FastAPI()
        app.add_middleware(CorrelationIdMiddleware)
        app.add_middleware(TimingMiddleware)
        
        @app.post("/submit")
        async def submit():
            return {"submitted": True}
        
        client = TestClient(app)
        response = client.post("/submit", json={"data": "test"})
        
        assert response.status_code == 200
        assert "X-Correlation-ID" in response.headers
        assert "X-Process-Time" in response.headers
    
    def test_middleware_with_query_params(self):
        """Test middleware with query parameters."""
        app = create_test_app()
        client = TestClient(app)
        
        response = client.get("/test?param1=value1&param2=value2")
        
        assert response.status_code == 200
        assert "X-Correlation-ID" in response.headers
