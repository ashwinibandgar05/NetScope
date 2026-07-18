from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.api.websocket import connection_manager

router = APIRouter()


@router.websocket("/ws/live")
async def live_feed(websocket: WebSocket):
    await connection_manager.connect(websocket)
    try:
        while True:
            # We don't expect inbound messages, but reading keeps the
            # connection alive and lets us detect client disconnects.
            await websocket.receive_text()
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
