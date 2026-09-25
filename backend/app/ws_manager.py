from __future__ import annotations

import json
from collections import defaultdict

from fastapi import WebSocket


class ConnectionManager:
    """Broadcasts JSON events to every browser tab connected to a given game."""

    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, code: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[code.upper()].add(websocket)

    def disconnect(self, code: str, websocket: WebSocket) -> None:
        key = code.upper()
        self._connections[key].discard(websocket)
        if not self._connections[key]:
            self._connections.pop(key, None)

    async def broadcast(self, code: str, event: str, data: dict) -> None:
        key = code.upper()
        message = json.dumps({"event": event, "data": data})
        dead: list[WebSocket] = []
        for connection in self._connections.get(key, set()):
            try:
                await connection.send_text(message)
            except Exception:
                dead.append(connection)
        for connection in dead:
            self.disconnect(key, connection)
