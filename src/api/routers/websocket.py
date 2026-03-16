"""WebSocket endpoints."""

from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.api.websocket import manager

router = APIRouter(tags=["websocket"])


@router.websocket("/logs")
async def websocket_logs(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time log streaming."""
    await manager.connect(websocket)

    await websocket.send_json({
        "type": "log",
        "level": "INFO",
        "message": "WebSocket connection established successfully",
        "timestamp": datetime.now().isoformat(),
    })

    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
