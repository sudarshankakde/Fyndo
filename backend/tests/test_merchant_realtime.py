"""Client requirement 9: live alert to the store when a shopper claims a coupon."""
import asyncio

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.main import app
from tests.feature_helpers import (
    bearer,
    prepare_schema,
    reel_payload,
    seed_store,
    seed_user,
    set_auto_approve,
)


@pytest.fixture
def setup():
    asyncio.run(prepare_schema())
    asyncio.run(set_auto_approve(True))
    store = asyncio.run(seed_store(with_staff=True))
    shopper = asyncio.run(seed_user(full_name="Sudarshan"))
    yield store, shopper
    asyncio.run(set_auto_approve(False))


def _coupon_template_id(client: TestClient, store) -> str:
    reel_id = client.post(
        "/api/v1/reels", json=reel_payload(), headers=bearer(store.owner_token)
    ).json()["data"]["reel_id"]
    reel = client.get(f"/api/v1/reels/{reel_id}").json()["data"]
    return reel["coupon"]["id"]


def test_socket_rejects_missing_or_foreign_token(setup):
    store, (_, shopper_token) = setup
    url = f"/api/v1/ws/merchants/{store.merchant_id}"
    with TestClient(app) as client:
        for query in ("", f"?token={shopper_token}"):
            with pytest.raises(WebSocketDisconnect) as exc:
                with client.websocket_connect(url + query) as ws:
                    ws.receive_json()
            assert exc.value.code == 1008


def test_owner_and_cashier_receive_coupon_enrolled_event(setup):
    store, (_, shopper_token) = setup
    url = f"/api/v1/ws/merchants/{store.merchant_id}"
    with TestClient(app) as client:
        template_id = _coupon_template_id(client, store)
        with client.websocket_connect(f"{url}?token={store.owner_token}") as owner_ws, \
                client.websocket_connect(f"{url}?token={store.staff_token}") as cashier_ws:
            assert owner_ws.receive_json()["event"] == "CONNECTED"
            assert cashier_ws.receive_json()["event"] == "CONNECTED"
            owner_ws.send_text("ping")
            assert owner_ws.receive_text() == "pong"

            claim = client.post(f"/api/v1/coupons/{template_id}/claim", headers=bearer(shopper_token))
            assert claim.status_code == 200, claim.text

            for ws in (owner_ws, cashier_ws):
                event = ws.receive_json()
                assert event["event"] == "COUPON_ENROLLED"
                assert event["data"]["coupon_template_id"] == template_id
                assert event["data"]["coupon_title"] == "Flat 20% OFF"
                assert event["data"]["shopper_name"] == "Sudarshan"

        inbox = client.get("/api/v1/notifications", headers=bearer(store.owner_token)).json()
        titles = [item["title"] for item in inbox["data"]["items"]]
        assert "New coupon claimed" in titles
