import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sensei.core.websocket import get_websocket_manager, ConnectionManager
from sensei.core.auth import get_current_user_from_token
from sensei.models.user import User

router = APIRouter()
logger = logging.getLogger(__name__)

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    manager: ConnectionManager = Depends(get_websocket_manager)
):
    auth_header = websocket.headers.get("authorization")
    token = None
    if auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1].strip()
    if not token:
        token = websocket.query_params.get("token")

    if not token:
        await websocket.close(code=1008)
        return

    user: User | None = await get_current_user_from_token(token)
    if not user:
        await websocket.close(code=1008)
        return

    user_id = str(user.id)
    await manager.connect(websocket, user_id)
    
    try:
        while True:
            # Handle incoming messages if needed
            data = await websocket.receive_text()
            logger.info(f"Received message from user {user_id}: {data}")
            # Echo back for heartbeat testing
            await websocket.send_text(f"Message received: {data}")
    except WebSocketDisconnect:
        await manager.disconnect(websocket, user_id)
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
        await manager.disconnect(websocket, user_id)
