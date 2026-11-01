import asyncio
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.main import app
from app.services.notification_service import NotificationService
from app.core.database import async_session_factory
from tests.feature_helpers import prepare_schema, seed_user


@pytest.fixture
def setup_user():
    from app.core.database import engine

    engine.sync_engine.pool = engine.sync_engine.pool.recreate()

    async def _init():
        await prepare_schema()
        shopper = await seed_user(full_name="Websocket Shopper")
        return shopper

    shopper = asyncio.run(_init())
    engine.sync_engine.pool = engine.sync_engine.pool.recreate()
    yield shopper
    engine.sync_engine.pool = engine.sync_engine.pool.recreate()


def test_notification_socket_rejects_missing_or_invalid_token():
    with TestClient(app) as client:
        with pytest.raises(WebSocketDisconnect) as exc:
            with client.websocket_connect("/api/v1/ws/notifications") as ws:
                ws.receive_json()
        assert exc.value.code == 1008

        with pytest.raises(WebSocketDisconnect) as exc:
            with client.websocket_connect("/api/v1/ws/notifications?token=invalid_token_123") as ws:
                ws.receive_json()
        assert exc.value.code == 1008


def test_notification_socket_connects_and_pongs(setup_user):
    user_id, token = setup_user
    with TestClient(app) as client:
        with client.websocket_connect(f"/api/v1/ws/notifications?token={token}") as ws:
            connected = ws.receive_json()
            assert connected["event"] == "CONNECTED"
            assert connected["data"]["user_id"] == str(user_id)
            assert isinstance(connected["data"]["unread_count"], int)

            ws.send_text("ping")
            assert ws.receive_text() == "pong"


def test_notification_socket_receives_unread_count_on_mark_all_read(setup_user):
    user_id, token = setup_user
    with TestClient(app) as client:
        with client.websocket_connect(f"/api/v1/ws/notifications?token={token}") as ws:
            connected = ws.receive_json()
            assert connected["event"] == "CONNECTED"
            assert connected["data"]["user_id"] == str(user_id)

            # Mark all as read triggers real-time WebSocket broadcast
            headers = {"Authorization": f"Bearer {token}"}
            res = client.post("/api/v1/notifications/read-all", headers=headers)
            assert res.status_code == 200

            event = ws.receive_json()
            assert event["event"] == "UNREAD_COUNT"
            assert event["data"]["unread_count"] == 0
