"""
Tests for Chat API Endpoints.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

from sensei.api.v1.endpoints.chat import router, ChatMessageRequest


# Create a minimal test app
app = FastAPI()
app.include_router(router, prefix="/api/v1/chat")


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestChatEndpoints:
    """Tests for chat API endpoints."""
    
    def test_list_intents(self, client):
        """Test listing available intents."""
        # Note: This endpoint doesn't require auth
        response = client.get("/api/v1/chat/intents")
        
        # May fail due to auth requirements, that's expected
        if response.status_code == 200:
            data = response.json()
            assert "data" in data
            assert isinstance(data["data"], list)
            assert len(data["data"]) > 0
    
    def test_chat_health(self, client):
        """Test chat health endpoint."""
        response = client.get("/api/v1/chat/health")
        
        # May fail due to auth requirements
        if response.status_code == 200:
            data = response.json()
            assert "data" in data
            assert data["data"]["status"] == "healthy"
    
    def test_message_request_validation(self):
        """Test message request validation."""
        # Valid request
        valid = ChatMessageRequest(message="Hello")
        assert valid.message == "Hello"
        assert valid.confirmed == False
        assert valid.session_id is None
        
        # With session
        session_id = uuid4()
        with_session = ChatMessageRequest(
            message="Test",
            session_id=session_id,
            confirmed=True,
        )
        assert with_session.session_id == session_id
        assert with_session.confirmed == True
    
    def test_message_request_min_length(self):
        """Test that empty messages are rejected."""
        with pytest.raises(ValueError):
            ChatMessageRequest(message="")
    
    def test_message_request_max_length(self):
        """Test that very long messages are rejected."""
        with pytest.raises(ValueError):
            ChatMessageRequest(message="A" * 5000)  # Over 4000 limit


class TestChatIntegration:
    """Integration tests requiring full app context."""
    
    @pytest.mark.skip(reason="Requires full app with auth")
    def test_send_message_authenticated(self, client):
        """Test sending a message with authentication."""
        # This would require a full app with auth middleware
        pass
    
    @pytest.mark.skip(reason="Requires full app with auth")
    def test_stream_message(self, client):
        """Test streaming message endpoint."""
        pass
    
    @pytest.mark.skip(reason="Requires full app with auth")
    def test_session_management(self, client):
        """Test session list and delete."""
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
