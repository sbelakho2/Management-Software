import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sensei.core.websocket import get_websocket_manager, ConnectionManager
from sensei.core.auth import get_current_user_from_token
from sensei.models.user import User

router = APIRouter()
logger = logging.getLogger(__name__)

@router.websocket("/ws/{token}")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str,
    manager: ConnectionManager = Depends(get_websocket_manager)
):
    user: User = await get_current_user_from_token(token)
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
        manager.disconnect(websocket, user_id)
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
        manager.disconnect(websocket, user_id)
