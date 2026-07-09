from collections import defaultdict

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self._rooms: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, delivery_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._rooms[delivery_id].add(websocket)

    def disconnect(self, delivery_id: str, websocket: WebSocket) -> None:
        self._rooms[delivery_id].discard(websocket)
        if not self._rooms[delivery_id]:
            self._rooms.pop(delivery_id, None)

    async def broadcast(self, delivery_id: str, message: dict[str, object]) -> None:
        stale: list[WebSocket] = []
        for connection in self._rooms.get(delivery_id, set()).copy():
            try:
                await connection.send_json(message)
            except Exception:
                stale.append(connection)
        for connection in stale:
            self.disconnect(delivery_id, connection)


manager = ConnectionManager()
