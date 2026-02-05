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


# =============================================================================
# Leader Election for Distributed Scheduling
# =============================================================================

import uuid
import asyncio
from datetime import datetime, timezone

# Unique instance identifier for this process
_INSTANCE_ID = str(uuid.uuid4())[:8]


async def acquire_leader_lock(
    lock_name: str,
    ttl_seconds: int = 60,
    instance_id: str | None = None,
) -> bool:
    """
    Attempt to acquire a distributed leader lock using Redis.
    
    This implements leader election for horizontal scaling scenarios where only
    one instance should run schedulers/background jobs.
    
    Args:
        lock_name: Name of the lock (e.g., "backup_scheduler_leader")
        ttl_seconds: Lock TTL in seconds (should be > heartbeat interval)
        instance_id: Optional custom instance identifier
    
    Returns:
        True if lock was acquired (this instance is leader), False otherwise.
    
    Usage:
        if await acquire_leader_lock("backup_scheduler_leader"):
            # Start the scheduler
            scheduler.start()
    """
    instance = instance_id or _INSTANCE_ID
    lock_key = f"sensei:leader:{lock_name}"
    
    try:
        # SET NX (only if not exists) with TTL
        # This is atomic and race-condition safe
        result = await redis_client.set(
            lock_key,
            instance,
            nx=True,  # Only set if not exists
            ex=ttl_seconds,
        )
        
        if result:
            return True
        
        # Check if we already own the lock
        current_holder = await redis_client.get(lock_key)
        return current_holder == instance
        
    except Exception:
        # If Redis is down, don't acquire (fail closed for safety)
        return False


async def renew_leader_lock(
    lock_name: str,
    ttl_seconds: int = 60,
    instance_id: str | None = None,
) -> bool:
    """
    Renew a leader lock if we own it.
    
    Should be called periodically (e.g., ttl_seconds / 2) to maintain leadership.
    
    Returns:
        True if renewal succeeded, False if we lost leadership.
    """
    instance = instance_id or _INSTANCE_ID
    lock_key = f"sensei:leader:{lock_name}"
    
    try:
        # Check if we still own the lock
        current_holder = await redis_client.get(lock_key)
        if current_holder != instance:
            return False
        
        # Renew the TTL
        await redis_client.expire(lock_key, ttl_seconds)
        return True
        
    except Exception:
        return False


async def release_leader_lock(
    lock_name: str,
    instance_id: str | None = None,
) -> bool:
    """
    Release a leader lock if we own it.
    
    Should be called during graceful shutdown.
    
    Returns:
        True if lock was released, False if we didn't own it.
    """
    instance = instance_id or _INSTANCE_ID
    lock_key = f"sensei:leader:{lock_name}"
    
    try:
        # Only delete if we own it (use Lua script for atomicity)
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        result = await redis_client.eval(lua_script, 1, lock_key, instance)
        return result == 1
        
    except Exception:
        return False


def get_instance_id() -> str:
    """Get the unique identifier for this process instance."""
    return _INSTANCE_ID
