"""
Base utilities for Today Screen service.

Contains core infrastructure like InMemoryRedis, UUIDEncoder, and BaseRedisStore.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, date
from enum import Enum
from typing import Any, Dict
from uuid import UUID

logger = logging.getLogger(__name__)


class UUIDEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles UUIDs, datetime, and Enum."""
    
    def default(self, obj: Any) -> Any:
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, Enum):
            return obj.value
        return super().default(obj)


class InMemoryRedis:
    """In-memory Redis mock for testing and local development."""
    
    def __init__(self) -> None:
        self._hashes: dict[str, dict[str, Any]] = {}

    async def hgetall(self, key: str) -> dict[str, Any]:
        return dict(self._hashes.get(key, {}))

    async def hset(
        self,
        key: str,
        field: str | None = None,
        value: Any | None = None,
        mapping: dict[str, Any] | None = None,
    ) -> None:
        bucket = self._hashes.setdefault(key, {})
        if mapping:
            bucket.update(mapping)
        elif field is not None and value is not None:
            bucket[field] = value

    async def delete(self, key: str) -> None:
        self._hashes.pop(key, None)

    async def hdel(self, key: str, field: str) -> int:
        bucket = self._hashes.get(key)
        if not bucket or field not in bucket:
            return 0
        del bucket[field]
        return 1

    async def expire(self, key: str, _ttl: int) -> None:
        return None

    def pipeline(self, transaction: bool = True) -> "InMemoryRedis":
        return self

    async def execute(self) -> None:
        return None

    async def __aenter__(self) -> "InMemoryRedis":
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        return None


class BaseRedisStore:
    """Base class for Redis-backed stores with user-scoped data."""
    
    def __init__(self, redis_client: Any, store_name: str) -> None:
        self._redis = redis_client
        self._store_name = store_name
        self.logger = logging.getLogger(f"{__name__}.{store_name}")

    async def _get_store(self, user_id: UUID) -> Dict[str, Any]:
        """Get a user-specific store from Redis (using Hashes for atomicity)."""
        key = f"today:{user_id}:{self._store_name}"
        data = await self._redis.hgetall(key) if self._redis else {}
        if not data:
            return {}
        if isinstance(self._redis, InMemoryRedis):
            return dict(data)
        return {k: json.loads(v) for k, v in data.items()}

    async def _save_store(self, user_id: UUID, data: Dict[str, Any]) -> None:
        """Save a user-specific store to Redis (using Hashes)."""
        key = f"today:{user_id}:{self._store_name}"
        if not data:
            if self._redis:
                await self._redis.delete(key)
            return
        
        serialized = (
            data if isinstance(self._redis, InMemoryRedis)
            else {k: json.dumps(v, cls=UUIDEncoder) for k, v in data.items()}
        )
        async with self._redis.pipeline(transaction=True) as pipe:
            await pipe.delete(key)
            await pipe.hset(key, mapping=serialized)
            await pipe.expire(key, 86400)
            await pipe.execute()

    async def _get_global_store(self, store_name: str | None = None) -> Dict[str, Any]:
        """Get a global store from Redis."""
        name = store_name or self._store_name
        key = f"today:global:{name}"
        data = await self._redis.hgetall(key) if self._redis else {}
        if not data:
            return {}
        if isinstance(self._redis, InMemoryRedis):
            return dict(data)
        return {k: json.loads(v) for k, v in data.items()}

    async def _save_global_item(self, store_name: str, item_id: str, data: Any) -> None:
        """Save an item to a global store in Redis."""
        key = f"today:global:{store_name}"
        if self._redis:
            val = (
                data if isinstance(self._redis, InMemoryRedis)
                else json.dumps(data, cls=UUIDEncoder)
            )
            await self._redis.hset(key, item_id, val)
            await self._redis.expire(key, 86400)

    async def _delete_global_item(self, store_name: str, item_id: str) -> bool:
        """Delete an item from a global store."""
        key = f"today:global:{store_name}"
        return await self._redis.hdel(key, item_id) > 0
