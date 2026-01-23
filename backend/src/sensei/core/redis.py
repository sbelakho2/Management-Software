"""
Sensei OS Redis Module

Redis client for caching, session storage, and Celery job queue.
"""

from typing import Optional
import redis.asyncio as redis

from sensei.core.config import settings


def create_redis_client() -> redis.Redis:
    """Create and configure the Redis client."""
    return redis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
        max_connections=settings.REDIS_MAX_CONNECTIONS,
    )


redis_client = create_redis_client()


async def check_redis_connection(client: redis.Redis) -> bool:
    """Check if the Redis connection is healthy."""
    try:
        await client.ping()  # type: ignore[misc]
        return True
    except Exception:
        return False


async def cache_get(key: str) -> Optional[str]:
    """Get a value from the cache."""
    return await redis_client.get(key)


async def cache_set(key: str, value: str, ttl_seconds: int = 3600) -> bool:
    """Set a value in the cache with TTL."""
    return await redis_client.set(key, value, ex=ttl_seconds)


async def cache_delete(key: str) -> int:
    """Delete a key from the cache."""
    return await redis_client.delete(key)


async def cache_exists(key: str) -> bool:
    """Check if a key exists in the cache."""
    return await redis_client.exists(key) > 0
