"""Comprehensive unit and integration tests for Merchant Subscription Gating on Reel Publishing.

Covers:
- Active merchant publishes reel -> 200/201 OK.
- Inactive merchant publishes reel -> HTTP 403 Forbidden with ErrorEnvelope.
- Expired merchant publishes reel -> HTTP 403 Forbidden with ErrorEnvelope.
- Dynamic expiration (ACTIVE status with past timestamp) -> HTTP 403 Forbidden.
- Cashier of inactive or expired store publishes reel -> HTTP 403 Forbidden.
- Active vs. expired reel validity extension -> 200 OK vs. HTTP 403 Forbidden.
- Non-upload endpoints (profile, insights, staff, categories) remain 200 OK for expired merchants.
- Pure service unit tests for ensure_active_subscription and is_subscription_active.
"""
from datetime import datetime, timedelta, timezone
import pytest
import pytest_asyncio
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.merchant import Merchant, SubscriptionStatus
from app.services.subscription_service import ensure_active_subscription, is_subscription_active
from tests.e2e_subscriptions.helpers import (
    assert_error_envelope,
    bearer,
    prepare_schema,
    reel_payload,
    seed_store,
    set_auto_approve,
    set_auto_approve_kyc,
    set_subscription_in_db,
    unique_phone,
    utcnow,
)

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture(autouse=True)
async def init_db():
    await prepare_schema()
    await set_auto_approve(True)
    await set_auto_approve_kyc(True)
    yield
    await set_auto_approve(False)
    await set_auto_approve_kyc(False)


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestSubscriptionServiceUnit:
    """Unit tests for subscription_service pure functions."""

    async def test_ensure_active_subscription_with_none_merchant(self):
        with pytest.raises(HTTPException) as exc_info:
            ensure_active_subscription(None)
        assert exc_info.value.status_code == 403
        assert "Active merchant subscription required" in exc_info.value.detail

    async def test_ensure_active_subscription_with_inactive_merchant(self):
        merchant = Merchant(
            subscription_status=SubscriptionStatus.INACTIVE,
            subscription_expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
        assert is_subscription_active(merchant) is False
        with pytest.raises(HTTPException) as exc_info:
            ensure_active_subscription(merchant)
        assert exc_info.value.status_code == 403

    async def test_ensure_active_subscription_with_expired_merchant(self):
        merchant = Merchant(
            subscription_status=SubscriptionStatus.ACTIVE,
            subscription_expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        assert is_subscription_active(merchant) is False
        with pytest.raises(HTTPException) as exc_info:
            ensure_active_subscription(merchant)
        assert exc_info.value.status_code == 403

    async def test_ensure_active_subscription_with_active_merchant(self):
        merchant = Merchant(
            subscription_status=SubscriptionStatus.ACTIVE,
            subscription_expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
        assert is_subscription_active(merchant) is True
        # Should not raise
        ensure_active_subscription(merchant)


class TestReelPublishingSubscriptionGate:
    """HTTP integration tests for reel publishing subscription enforcement."""

    async def test_active_merchant_publishes_reel_success(self, client: AsyncClient):
        store = await seed_store()
        future = utcnow() + timedelta(days=60)
        await set_subscription_in_db(store.merchant_id, status="ACTIVE", expires_at=future)

        resp = await client.post("/api/v1/reels", json=reel_payload(), headers=bearer(store.owner_token))
        assert resp.status_code in (200, 201), resp.text
        assert resp.json().get("success") is True

    async def test_inactive_merchant_publishes_reel_forbidden(self, client: AsyncClient):
        store = await seed_store()
        await set_subscription_in_db(store.merchant_id, status="INACTIVE")

        resp = await client.post("/api/v1/reels", json=reel_payload(), headers=bearer(store.owner_token))
        assert resp.status_code == 403, resp.text
        assert_error_envelope(
            resp.json(),
            expected_status_code=403,
            expected_code="HTTP_403",
            expected_message="Active merchant subscription required to publish reels",
        )

    async def test_expired_merchant_publishes_reel_forbidden(self, client: AsyncClient):
        store = await seed_store()
        past = utcnow() - timedelta(days=2)
        await set_subscription_in_db(store.merchant_id, status="EXPIRED", expires_at=past)

        resp = await client.post("/api/v1/reels", json=reel_payload(), headers=bearer(store.owner_token))
        assert resp.status_code == 403, resp.text
        assert_error_envelope(
            resp.json(),
            expected_status_code=403,
            expected_code="HTTP_403",
            expected_message="Active merchant subscription required to publish reels",
        )

    async def test_dynamically_expired_active_status_publishes_reel_forbidden(self, client: AsyncClient):
        store = await seed_store()
        past = utcnow() - timedelta(hours=3)
        await set_subscription_in_db(store.merchant_id, status="ACTIVE", expires_at=past)

        resp = await client.post("/api/v1/reels", json=reel_payload(), headers=bearer(store.owner_token))
        assert resp.status_code == 403, resp.text
        assert_error_envelope(resp.json(), expected_status_code=403, expected_code="HTTP_403")

    async def test_cashier_of_inactive_store_publishes_reel_forbidden(self, client: AsyncClient):
        store = await seed_store(with_staff=True, can_upload_reels=True)
        await set_subscription_in_db(store.merchant_id, status="INACTIVE")

        resp = await client.post("/api/v1/reels", json=reel_payload(), headers=bearer(store.staff_token))
        assert resp.status_code == 403, resp.text
        assert_error_envelope(resp.json(), expected_status_code=403, expected_code="HTTP_403")

    async def test_cashier_of_expired_store_publishes_reel_forbidden(self, client: AsyncClient):
        store = await seed_store(with_staff=True, can_upload_reels=True)
        past = utcnow() - timedelta(days=5)
        await set_subscription_in_db(store.merchant_id, status="EXPIRED", expires_at=past)

        resp = await client.post("/api/v1/reels", json=reel_payload(), headers=bearer(store.staff_token))
        assert resp.status_code == 403, resp.text
        assert_error_envelope(resp.json(), expected_status_code=403, expected_code="HTTP_403")


class TestReelExtendSubscriptionGate:
    """HTTP integration tests for offer validity extension subscription enforcement."""

    async def test_active_merchant_can_extend_validity(self, client: AsyncClient):
        store = await seed_store()
        future = utcnow() + timedelta(days=60)
        await set_subscription_in_db(store.merchant_id, status="ACTIVE", expires_at=future)

        create_res = await client.post("/api/v1/reels", json=reel_payload(validity_days=2), headers=bearer(store.owner_token))
        assert create_res.status_code in (200, 201)
        reel_id = create_res.json()["data"]["reel_id"]

        extend_res = await client.post(
            f"/api/v1/reels/{reel_id}/extend-validity",
            json={"additional_days": 3},
            headers=bearer(store.owner_token),
        )
        assert extend_res.status_code == 200, extend_res.text
        assert extend_res.json().get("success") is True

    async def test_expired_merchant_cannot_extend_validity(self, client: AsyncClient):
        store = await seed_store()
        future = utcnow() + timedelta(days=60)
        await set_subscription_in_db(store.merchant_id, status="ACTIVE", expires_at=future)

        create_res = await client.post("/api/v1/reels", json=reel_payload(validity_days=2), headers=bearer(store.owner_token))
        assert create_res.status_code in (200, 201)
        reel_id = create_res.json()["data"]["reel_id"]

        # Expire subscription
        past = utcnow() - timedelta(days=1)
        await set_subscription_in_db(store.merchant_id, status="EXPIRED", expires_at=past)

        extend_res = await client.post(
            f"/api/v1/reels/{reel_id}/extend-validity",
            json={"additional_days": 3},
            headers=bearer(store.owner_token),
        )
        assert extend_res.status_code == 403, extend_res.text
        assert_error_envelope(
            extend_res.json(),
            expected_status_code=403,
            expected_code="HTTP_403",
            expected_message="Active merchant subscription required to publish reels",
        )


class TestNonUploadEndpointsPreservation:
    """Verifies that non-upload endpoints remain 100% operational for expired/inactive merchants."""

    async def test_expired_merchant_accesses_all_non_upload_endpoints(self, client: AsyncClient):
        store = await seed_store(with_staff=True)
        past = utcnow() - timedelta(days=15)
        await set_subscription_in_db(store.merchant_id, status="EXPIRED", expires_at=past)

        # 1. Profile GET
        resp_profile = await client.get("/api/v1/merchants/profile", headers=bearer(store.owner_token))
        assert resp_profile.status_code == 200
        assert resp_profile.json().get("success") is True

        # 2. Insights / Analytics GET
        resp_insights = await client.get("/api/v1/merchants/me/insights", headers=bearer(store.owner_token))
        assert resp_insights.status_code == 200
        assert resp_insights.json().get("success") is True

        # 3. Staff list GET
        resp_staff_list = await client.get("/api/v1/merchants/staff", headers=bearer(store.owner_token))
        assert resp_staff_list.status_code == 200

        # 4. Staff create POST
        new_staff_payload = {
            "staff_name": "Shift Cashier",
            "phone": unique_phone(),
            "pin": "123456",
            "can_upload_reels": False,
        }
        resp_staff_create = await client.post(
            "/api/v1/merchants/staff",
            json=new_staff_payload,
            headers=bearer(store.owner_token),
        )
        assert resp_staff_create.status_code == 200

        # 5. Profile PATCH
        resp_patch = await client.patch(
            "/api/v1/merchants/profile",
            json={"business_hours": "10:00 AM - 10:00 PM"},
            headers=bearer(store.owner_token),
        )
        assert resp_patch.status_code == 200

        # 6. Categories GET
        resp_cats = await client.get("/api/v1/merchants/categories")
        assert resp_cats.status_code == 200
