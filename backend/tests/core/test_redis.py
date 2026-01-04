"""
Tests for Sensei Core Redis Module

Comprehensive tests for Redis caching operations with edge cases.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from sensei.core.redis import (
    cache_get,
    cache_set,
    cache_delete,
    cache_exists,
    check_redis_connection,
)


class TestCacheGet:
    """Tests for cache get operations."""
    
    @pytest.mark.asyncio
    @patch("sensei.core.redis.redis_client")
    async def test_get_existing_key(self, mock_client):
        """Test getting an existing key."""
        mock_client.get = AsyncMock(return_value="cached_value")
        
        result = await cache_get("test_key")
        
        assert result == "cached_value"
        mock_client.get.assert_called_once_with("test_key")
    
    @pytest.mark.asyncio
    @patch("sensei.core.redis.redis_client")
    async def test_get_nonexistent_key(self, mock_client):
        """Test getting a non-existent key returns None."""
        mock_client.get = AsyncMock(return_value=None)
        
        result = await cache_get("nonexistent_key")
        
        assert result is None
    
    @pytest.mark.asyncio
    @patch("sensei.core.redis.redis_client")
    async def test_get_empty_string_value(self, mock_client):
        """Test getting a key with empty string value."""
        mock_client.get = AsyncMock(return_value="")
        
        result = await cache_get("empty_value_key")
        
        assert result == ""


class TestCacheSet:
    """Tests for cache set operations."""
    
    @pytest.mark.asyncio
    @patch("sensei.core.redis.redis_client")
    async def test_set_with_default_ttl(self, mock_client):
        """Test setting a value with default TTL."""
        mock_client.set = AsyncMock(return_value=True)
        
        result = await cache_set("key", "value")
        
        assert result is True
        mock_client.set.assert_called_once_with("key", "value", ex=3600)
    
    @pytest.mark.asyncio
    @patch("sensei.core.redis.redis_client")
    async def test_set_with_custom_ttl(self, mock_client):
        """Test setting a value with custom TTL."""
        mock_client.set = AsyncMock(return_value=True)
        
        result = await cache_set("key", "value", ttl_seconds=300)
        
        mock_client.set.assert_called_once_with("key", "value", ex=300)
    
    @pytest.mark.asyncio
    @patch("sensei.core.redis.redis_client")
    async def test_set_empty_value(self, mock_client):
        """Test setting an empty string value."""
        mock_client.set = AsyncMock(return_value=True)
        
        result = await cache_set("key", "")
        
        assert result is True
        mock_client.set.assert_called_once_with("key", "", ex=3600)
    
    @pytest.mark.asyncio
    @patch("sensei.core.redis.redis_client")
    async def test_set_long_value(self, mock_client):
        """Test setting a long string value."""
        mock_client.set = AsyncMock(return_value=True)
        long_value = "x" * 100000
        
        result = await cache_set("key", long_value)
        
        assert result is True


class TestCacheDelete:
    """Tests for cache delete operations."""
    
    @pytest.mark.asyncio
    @patch("sensei.core.redis.redis_client")
    async def test_delete_existing_key(self, mock_client):
        """Test deleting an existing key."""
        mock_client.delete = AsyncMock(return_value=1)
        
        result = await cache_delete("existing_key")
        
        assert result == 1
        mock_client.delete.assert_called_once_with("existing_key")
    
    @pytest.mark.asyncio
    @patch("sensei.core.redis.redis_client")
    async def test_delete_nonexistent_key(self, mock_client):
        """Test deleting a non-existent key returns 0."""
        mock_client.delete = AsyncMock(return_value=0)
        
        result = await cache_delete("nonexistent_key")
        
        assert result == 0


class TestCacheExists:
    """Tests for cache exists operations."""
    
    @pytest.mark.asyncio
    @patch("sensei.core.redis.redis_client")
    async def test_exists_true(self, mock_client):
        """Test key exists returns True."""
        mock_client.exists = AsyncMock(return_value=1)
        
        result = await cache_exists("existing_key")
        
        assert result is True
    
    @pytest.mark.asyncio
    @patch("sensei.core.redis.redis_client")
    async def test_exists_false(self, mock_client):
        """Test key doesn't exist returns False."""
        mock_client.exists = AsyncMock(return_value=0)
        
        result = await cache_exists("nonexistent_key")
        
        assert result is False


class TestCheckRedisConnection:
    """Tests for Redis connection health checking."""
    
    @pytest.mark.asyncio
    async def test_connection_healthy(self):
        """Test healthy Redis connection."""
        mock_client = MagicMock()
        mock_client.ping = AsyncMock(return_value=True)
        
        result = await check_redis_connection(mock_client)
        
        assert result is True
        mock_client.ping.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_connection_unhealthy(self):
        """Test unhealthy Redis connection."""
        mock_client = MagicMock()
        mock_client.ping = AsyncMock(side_effect=Exception("Connection refused"))
        
        result = await check_redis_connection(mock_client)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_connection_timeout(self):
        """Test Redis connection timeout."""
        mock_client = MagicMock()
        mock_client.ping = AsyncMock(side_effect=TimeoutError("Connection timed out"))
        
        result = await check_redis_connection(mock_client)
        
        assert result is False
