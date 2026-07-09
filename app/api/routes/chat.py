from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.adapters import chat_store
from app.core.config import get_settings
from app.core.security import decode_token
from app.db.session import SessionLocal
from app.realtime.manager import manager
from app.services import delivery_service

router = APIRouter(tags=["delivery-chat"])


@router.websocket("/ws/deliveries/{delivery_id}/chat")
async def delivery_chat(websocket: WebSocket, delivery_id: str, token: str) -> None:
    try:
        principal = decode_token(token, get_settings())
        with SessionLocal() as db:
            delivery = delivery_service.get_delivery(db, delivery_id)
            delivery_service.assert_access(delivery, principal)
    except Exception:
        await websocket.close(code=4403)
        return

    await manager.connect(delivery_id, websocket)
    try:
        while True:
            payload = await websocket.receive_json()
            text = payload.get("text") if isinstance(payload, dict) else None
            if not isinstance(text, str) or not 1 <= len(text.strip()) <= 2000:
                await websocket.send_json({"error": "Message must be 1-2000 characters"})
                continue
            message = chat_store.message(
                delivery_id=delivery_id,
                sender_id=principal.user_id,
                sender_role=principal.role,
                text=text.strip(),
            )
            chat_store.save_message(message)
            wire_message = {**message, "sent_at": message["sent_at"].isoformat()}
            await manager.broadcast(delivery_id, wire_message)
    except WebSocketDisconnect:
        manager.disconnect(delivery_id, websocket)
