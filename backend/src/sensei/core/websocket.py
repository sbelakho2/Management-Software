import json
import logging
from typing import Dict, Set, Any
from fastapi import WebSocket

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # active connections: {user_id: {websocket}}
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        logger.info(f"User {user_id} connected via WebSocket. Active users: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"User {user_id} disconnected from WebSocket.")

    async def send_personal_message(self, message: Any, user_id: str):
        if user_id in self.active_connections:
            data = json.dumps(message)
            for websocket in self.active_connections[user_id]:
                try:
                    await websocket.send_text(data)
                except Exception as e:
                    logger.error(f"Failed to send message to user {user_id}: {e}")

    async def broadcast(self, message: Any):
        data = json.dumps(message)
        for user_id, connections in self.active_connections.items():
            for websocket in connections:
                try:
                    await websocket.send_text(data)
                except Exception as e:
                    logger.error(f"Failed to broadcast message to user {user_id}: {e}")

manager = ConnectionManager()

def get_websocket_manager() -> ConnectionManager:
    return manager
