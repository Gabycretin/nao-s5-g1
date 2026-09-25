from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..state import ws_manager

router = APIRouter()


@router.websocket("/ws/games/{code}")
async def game_ws(websocket: WebSocket, code: str) -> None:
    await ws_manager.connect(code, websocket)
    try:
        while True:
            # Clients don't send anything meaningful; this just keeps the
            # connection open so we notice disconnects.
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(code, websocket)
