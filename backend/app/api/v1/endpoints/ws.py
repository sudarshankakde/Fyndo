"""Real-time channel for store screens (owner dashboard and cashier terminal).

Browsers cannot set an Authorization header on a WebSocket, so the access
token travels as the ``token`` query parameter:

    ws://host/api/v1/ws/merchants/{merchant_id}?token=<access token>

Events are JSON objects shaped ``{"event": "...", "data": {...}}``. Sending the
text ``ping`` returns ``pong`` so clients can keep the connection warm.
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select

from app.core.database import async_session_factory, ensure_compatibility_schema
from app.core.security import decode_access_token
from app.models.merchant import Merchant, MerchantStaff
from app.models.user import User
from app.services.socket_service import merchant_sockets

router = APIRouter()

WS_POLICY_VIOLATION = status.WS_1008_POLICY_VIOLATION


async def _authorised_for(merchant_id: uuid.UUID, token: Optional[str]) -> bool:
    payload = decode_access_token(token) if token else None
    if not payload or "sub" not in payload:
        return False
    try:
        subject_id = uuid.UUID(payload["sub"])
    except (ValueError, TypeError):
        return False

    await ensure_compatibility_schema()
    async with async_session_factory() as db:
        if payload.get("role") == "ROLE_CASHIER":
            staff = await db.get(MerchantStaff, subject_id)
            return bool(staff and staff.is_active and staff.merchant_id == merchant_id)
        owner_id = (
            await db.execute(select(Merchant.user_id).where(Merchant.id == merchant_id))
        ).scalar_one_or_none()
        if owner_id != subject_id:
            return False
        user = await db.get(User, subject_id)
        return bool(user and user.is_active)


@router.websocket("/ws/merchants/{merchant_id}")
async def merchant_events(
    websocket: WebSocket,
    merchant_id: uuid.UUID,
    token: Optional[str] = Query(None),
):
    if not await _authorised_for(merchant_id, token):
        await websocket.close(code=WS_POLICY_VIOLATION)
        return

    key = str(merchant_id)
    await merchant_sockets.connect(key, websocket)
    try:
        await websocket.send_json({"event": "CONNECTED", "data": {"merchant_id": key}})
        while True:
            message = await websocket.receive_text()
            if message == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    finally:
        await merchant_sockets.disconnect(key, websocket)
