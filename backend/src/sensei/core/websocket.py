import json
import logging
import asyncio
import time
from typing import Dict, Set, Any, Optional
from fastapi import WebSocket

logger = logging.getLogger(__name__)


# =============================================================================
# Redis Pub/Sub Adapter for Multi-Instance WebSocket Support
# =============================================================================

_REDIS_WS_CHANNEL = "sensei:ws:broadcast"
_REDIS_WS_USER_PREFIX = "sensei:ws:user:"


class RedisPubSubAdapter:
    """Bridges WebSocket messages across multiple server instances via Redis Pub/Sub.

    Without this adapter, a message sent from instance A is never delivered to
    WebSocket clients connected to instance B. This adapter:
    1. Publishes all outgoing messages to a Redis channel.
    2. Subscribes to that channel and forwards messages to local clients.
    """

    def __init__(self) -> None:
        self._pubsub = None
        self._listener_task: Optional[asyncio.Task] = None
        self._manager: Optional["ConnectionManager"] = None
        self._running = False

    async def start(self, manager: "ConnectionManager") -> None:
        """Start listening for Redis pub/sub messages."""
        self._manager = manager
        try:
            from sensei.core.redis import redis_client
            self._pubsub = redis_client.pubsub()
            await self._pubsub.subscribe(_REDIS_WS_CHANNEL)
            self._running = True
            self._listener_task = asyncio.create_task(self._listen())
            logger.info("Redis WebSocket pub/sub adapter started")
        except Exception as e:
            logger.warning(f"Redis pub/sub unavailable, WebSocket limited to single instance: {e}")
            self._running = False

    async def stop(self) -> None:
        """Stop listening for Redis pub/sub messages."""
        self._running = False
        if self._listener_task and not self._listener_task.done():
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        if self._pubsub:
            try:
                await self._pubsub.unsubscribe(_REDIS_WS_CHANNEL)
                await self._pubsub.close()
            except Exception:
                pass
        logger.info("Redis WebSocket pub/sub adapter stopped")

    async def publish(self, message: dict) -> None:
        """Publish a message to all instances via Redis."""
        if not self._running:
            return
        try:
            from sensei.core.redis import redis_client
            await redis_client.publish(_REDIS_WS_CHANNEL, json.dumps(message))
        except Exception as e:
            logger.warning(f"Failed to publish WebSocket message to Redis: {e}")

    async def _listen(self) -> None:
        """Listen for messages from other instances and deliver locally."""
        while self._running:
            try:
                if self._pubsub is None:
                    await asyncio.sleep(1)
                    continue
                message = await self._pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1.0
                )
                if message and message["type"] == "message":
                    data = json.loads(message["data"])
                    target_user = data.get("target_user_id")
                    payload = data.get("payload")
                    if target_user and self._manager:
                        await self._manager._deliver_local(payload, target_user)
                    elif payload and self._manager:
                        await self._manager._broadcast_local(payload)
            except asyncio.CancelledError:
                return
            except Exception as e:
                logger.error(f"Redis pub/sub listener error: {e}")
                await asyncio.sleep(1)


# =============================================================================
# Connection Manager with Redis Pub/Sub Support
# =============================================================================


class ConnectionManager:
    """WebSocket connection manager with Redis pub/sub for multi-instance deployments.

    Local connections are tracked in-memory (required for holding WebSocket refs).
    Cross-instance message delivery uses Redis pub/sub.
    Connection limits prevent resource exhaustion:
    - MAX_CONNECTIONS_PER_USER: prevents a single user from hogging resources
    - MAX_TOTAL_CONNECTIONS: prevents overall memory exhaustion
    """

    MAX_CONNECTIONS_PER_USER = 5
    MAX_TOTAL_CONNECTIONS = 500

    def __init__(self):
        # active connections: {user_id: {websocket}}
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()
        self._last_seen: Dict[WebSocket, float] = {}
        self._heartbeat_interval = 30.0
        self._stale_threshold = 90.0
        self._pubsub_adapter = RedisPubSubAdapter()
        self._total_connections = 0

    async def initialize(self) -> None:
        """Initialize the Redis pub/sub adapter. Call during app startup."""
        await self._pubsub_adapter.start(self)

    async def shutdown(self) -> None:
        """Shutdown the Redis pub/sub adapter. Call during app shutdown."""
        await self._pubsub_adapter.stop()

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        async with self._lock:
            # Enforce total connection limit
            if self._total_connections >= self.MAX_TOTAL_CONNECTIONS:
                logger.warning(
                    f"Max total WebSocket connections reached ({self.MAX_TOTAL_CONNECTIONS}), rejecting {user_id}"
                )
                await websocket.close(code=1013, reason="Server overloaded")
                return
            # Enforce per-user connection limit
            user_conns = self.active_connections.get(user_id, set())
            if len(user_conns) >= self.MAX_CONNECTIONS_PER_USER:
                # Close oldest connection for this user
                oldest = min(user_conns, key=lambda ws: self._last_seen.get(ws, 0))
                try:
                    await oldest.close(code=1000, reason="Connection replaced")
                except Exception:
                    pass
                user_conns.discard(oldest)
                if oldest in self._last_seen:
                    del self._last_seen[oldest]
                self._total_connections -= 1
            if user_id not in self.active_connections:
                self.active_connections[user_id] = set()
            self.active_connections[user_id].add(websocket)
            self._last_seen[websocket] = time.time()
            self._total_connections += 1
        logger.info(f"User {user_id} connected via WebSocket. Active users: {len(self.active_connections)}, total: {self._total_connections}")

    async def disconnect(self, websocket: WebSocket, user_id: str):
        async with self._lock:
            if user_id in self.active_connections:
                self.active_connections[user_id].discard(websocket)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
            if websocket in self._last_seen:
                del self._last_seen[websocket]
            self._total_connections = max(0, self._total_connections - 1)
        logger.info(f"User {user_id} disconnected from WebSocket. Total: {self._total_connections}")

    async def send_personal_message(self, message: Any, user_id: str):
        """Send a message to a user across ALL server instances."""
        # Deliver locally first
        await self._deliver_local(message, user_id)
        # Publish to Redis for other instances
        await self._pubsub_adapter.publish({
            "target_user_id": user_id,
            "payload": message,
        })

    async def broadcast(self, message: Any):
        """Broadcast a message to ALL connected users across ALL instances."""
        await self._broadcast_local(message)
        await self._pubsub_adapter.publish({
            "target_user_id": None,
            "payload": message,
        })

    async def _deliver_local(self, message: Any, user_id: str):
        """Deliver a message to locally connected sockets for a user."""
        data = json.dumps(message) if not isinstance(message, str) else message
        async with self._lock:
            connections = list(self.active_connections.get(user_id, set()))
        for websocket in connections:
            try:
                await websocket.send_text(data)
                self._last_seen[websocket] = time.time()
            except Exception as e:
                logger.error(f"Failed to send message to user {user_id}: {e}")
                async with self._lock:
                    self.active_connections.get(user_id, set()).discard(websocket)
                    if websocket in self._last_seen:
                        del self._last_seen[websocket]

    async def _broadcast_local(self, message: Any):
        """Broadcast a message to all locally connected sockets."""
        data = json.dumps(message) if not isinstance(message, str) else message
        async with self._lock:
            snapshot = {user_id: list(connections) for user_id, connections in self.active_connections.items()}
        for user_id, connections in snapshot.items():
            for websocket in connections:
                try:
                    await websocket.send_text(data)
                    self._last_seen[websocket] = time.time()
                except Exception as e:
                    logger.error(f"Failed to broadcast message to user {user_id}: {e}")
                    async with self._lock:
                        self.active_connections.get(user_id, set()).discard(websocket)
                        if websocket in self._last_seen:
                            del self._last_seen[websocket]

    def start_heartbeat(self, websocket: WebSocket, user_id: str) -> asyncio.Task:
        """Start a heartbeat task to keep connections fresh and remove stale sockets."""
        async def _heartbeat_loop() -> None:
            while True:
                await asyncio.sleep(self._heartbeat_interval)
                last_seen = self._last_seen.get(websocket)
                if last_seen is None:
                    return
                if time.time() - last_seen > self._stale_threshold:
                    try:
                        await websocket.close()
                    finally:
                        await self.disconnect(websocket, user_id)
                    return
                try:
                    await websocket.send_text(json.dumps({"type": "ping"}))
                except Exception:
                    await self.disconnect(websocket, user_id)
                    return

        return asyncio.create_task(_heartbeat_loop())

    def stop_heartbeat(self, task: asyncio.Task | None) -> None:
        if task and not task.done():
            task.cancel()

    def get_connected_user_count(self) -> int:
        """Return the number of users with active local connections."""
        return len(self.active_connections)


manager = ConnectionManager()

def get_websocket_manager() -> ConnectionManager:
    return manager
