"""
Pytest Configuration and Fixtures

Shared fixtures and configuration for all tests.
"""

import os
import pytest
from unittest.mock import patch

# Set test environment variables before importing settings
os.environ.setdefault("SECRET_KEY", "test_secret_key_that_is_at_least_32_chars")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("DATABASE_URL_SYNC", "postgresql://test:test@localhost/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("S3_ENDPOINT", "http://localhost:9000")
os.environ.setdefault("ENVIRONMENT", "development")


@pytest.fixture(scope="session")
def test_settings():
    """Provide test settings."""
    from sensei.core.config import Settings
    
    return Settings(
        SECRET_KEY="test_secret_key_that_is_at_least_32_chars",
        DATABASE_URL="postgresql+asyncpg://test:test@localhost/test",
        DATABASE_URL_SYNC="postgresql://test:test@localhost/test",
        REDIS_URL="redis://localhost:6379/0",
        S3_ENDPOINT="http://localhost:9000",
        S3_ACCESS_KEY="test_key",
        S3_SECRET_KEY="test_secret",
        ENVIRONMENT="development",
    )


@pytest.fixture
def mock_db_session():
    """Provide a mock database session."""
    from unittest.mock import AsyncMock, MagicMock
    
    session = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.delete = MagicMock()
    
    return session


@pytest.fixture
def mock_redis_client():
    """Provide a mock Redis client."""
    from unittest.mock import AsyncMock, MagicMock
    
    client = MagicMock()
    client.get = AsyncMock(return_value=None)
    client.set = AsyncMock(return_value=True)
    client.delete = AsyncMock(return_value=1)
    client.exists = AsyncMock(return_value=0)
    client.ping = AsyncMock(return_value=True)
    
    return client


@pytest.fixture
def mock_storage_client():
    """Provide a mock S3 storage client."""
    from unittest.mock import MagicMock
    
    client = MagicMock()
    client.put_object = MagicMock(return_value={})
    client.get_object = MagicMock()
    client.delete_object = MagicMock()
    client.head_bucket = MagicMock()
    client.create_bucket = MagicMock()
    client.list_objects_v2 = MagicMock(return_value={"Contents": []})
    client.generate_presigned_url = MagicMock(return_value="https://example.com/file")
    
    return client


@pytest.fixture
def sample_file_content():
    """Provide sample file content for testing."""
    return b"Sample file content for testing purposes"


@pytest.fixture
def sample_pdf_content():
    """Provide sample PDF-like content for testing."""
    # Minimal PDF header
    return b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\ntrailer\n<<\n/Root 1 0 R\n>>\n%%EOF"


@pytest.fixture
def sample_user_data():
    """Provide sample user data for testing."""
    return {
        "email": "test@example.com",
        "full_name": "Test User",
        "role": "gm",
        "is_active": True,
    }


@pytest.fixture
def sample_rfq_data():
    """Provide sample RFQ data for testing."""
    return {
        "customer_id": "cust_123",
        "product_family": "Electronics",
        "annual_volume": 10000,
        "target_price": 15.50,
        "incoterms": "DDP",
        "location": "Morocco",
    }


@pytest.fixture
def sample_quote_data():
    """Provide sample quote data for testing."""
    return {
        "rfq_id": "rfq_123",
        "customer_id": "cust_123",
        "validity_days": 30,
        "moq": 1000,
        "lead_time_weeks": 8,
        "unit_price": 18.00,
        "assumptions": ["Material prices valid for 30 days", "Volume commitment required"],
    }
