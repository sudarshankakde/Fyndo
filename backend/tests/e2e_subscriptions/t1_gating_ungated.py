"""Tier 1 - Features 6 & 7: Reel Upload Gating (HTTP 403) & Non-Upload Preservation."""
from datetime import timedelta
import pytest
from httpx import AsyncClient

from tests.e2e_subscriptions.helpers import (
    assert_error_envelope,
    bearer,
    reel_payload,
    seed_store,
    seed_user,
    set_subscription_in_db,
    unique_phone,
    utcnow,
)

pytestmark = pytest.mark.asyncio


class TestTier1ContentGating:
    """Tier 1: Feature 6 - Content Upload Gating on Reel Publishing (HTTP 403)."""

    async def test_tier1_reel_publishing_allowed_for_active_trial_merchant(self, client: AsyncClient):
        """Active trial merchant can publish new showcase reels successfully."""
        store = await seed_store()
        future = utcnow() + timedelta(days=60)
        await set_subscription_in_db(store.merchant_id, status="ACTIVE", expires_at=future)

        resp = await client.post("/api/v1/reels", json=reel_payload(), headers=bearer(store.owner_token))
        assert resp.status_code in (200, 201), resp.text
        assert resp.json().get("success") is True

    async def test_tier1_reel_publishing_blocked_for_expired_merchant(self, client: AsyncClient):
        """Expired merchant cannot publish reels and receives HTTP 403."""
        store = await seed_store()
        past = utcnow() - timedelta(days=1)
        await set_subscription_in_db(store.merchant_id, status="EXPIRED", expires_at=past)

        resp = await client.post("/api/v1/reels", json=reel_payload(), headers=bearer(store.owner_token))
        assert resp.status_code == 403, resp.text
        assert_error_envelope(resp.json(), expected_status_code=403, expected_code="HTTP_403")

    async def test_tier1_reel_publishing_blocked_for_inactive_merchant(self, client: AsyncClient):
        """Inactive merchant cannot publish reels and receives HTTP 403."""
        store = await seed_store()
        await set_subscription_in_db(store.merchant_id, status="INACTIVE")

        resp = await client.post("/api/v1/reels", json=reel_payload(), headers=bearer(store.owner_token))
        assert resp.status_code == 403, resp.text
        assert_error_envelope(resp.json(), expected_status_code=403, expected_code="HTTP_403")

    async def test_tier1_reel_publishing_error_envelope_format_and_message(self, client: AsyncClient):
        """Reel publishing 403 response contains the exact required error envelope and message."""
        store = await seed_store()
        past = utcnow() - timedelta(days=5)
        await set_subscription_in_db(store.merchant_id, status="EXPIRED", expires_at=past)

        resp = await client.post("/api/v1/reels", json=reel_payload(), headers=bearer(store.owner_token))
        assert resp.status_code == 403
        data = resp.json()
        expected_msg = "Active merchant subscription required to publish reels. Your subscription is inactive or expired."
        assert_error_envelope(data, expected_status_code=403, expected_code="HTTP_403", expected_message=expected_msg)

    async def test_tier1_reel_publishing_blocked_for_cashier_of_expired_store(self, client: AsyncClient):
        """Cashier of an expired store is blocked from publishing reels despite having staff upload permission."""
        store = await seed_store(with_staff=True, can_upload_reels=True)
        past = utcnow() - timedelta(days=2)
        await set_subscription_in_db(store.merchant_id, status="EXPIRED", expires_at=past)

        resp = await client.post("/api/v1/reels", json=reel_payload(), headers=bearer(store.staff_token))
        assert resp.status_code == 403, resp.text
        assert_error_envelope(resp.json(), expected_status_code=403, expected_code="HTTP_403")


class TestTier1NonUploadPreservation:
    """Tier 1: Feature 7 - Non-Upload Endpoints Preservation for Inactive/Expired Merchants."""

    async def test_tier1_non_upload_profile_accessible_when_expired(self, client: AsyncClient):
        """Expired merchant can access GET /api/v1/merchants/profile (HTTP 200)."""
        store = await seed_store()
        past = utcnow() - timedelta(days=10)
        await set_subscription_in_db(store.merchant_id, status="EXPIRED", expires_at=past)

        resp = await client.get("/api/v1/merchants/profile", headers=bearer(store.owner_token))
        assert resp.status_code == 200, resp.text
        assert resp.json().get("success") is True

    async def test_tier1_non_upload_profile_update_accessible_when_expired(self, client: AsyncClient):
        """Expired merchant can update store details via PATCH /api/v1/merchants/profile (HTTP 200)."""
        store = await seed_store()
        past = utcnow() - timedelta(days=10)
        await set_subscription_in_db(store.merchant_id, status="EXPIRED", expires_at=past)

        payload = {"business_hours": "Mon-Sat 10:00 AM - 9:00 PM"}
        resp = await client.patch("/api/v1/merchants/profile", json=payload, headers=bearer(store.owner_token))
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"].get("business_hours") == payload["business_hours"]

    async def test_tier1_non_upload_insights_analytics_accessible_when_expired(self, client: AsyncClient):
        """Expired merchant can view dashboard analytics & insights (HTTP 200)."""
        store = await seed_store()
        past = utcnow() - timedelta(days=10)
        await set_subscription_in_db(store.merchant_id, status="EXPIRED", expires_at=past)

        resp = await client.get("/api/v1/merchants/me/insights", headers=bearer(store.owner_token))
        assert resp.status_code == 200, resp.text

    async def test_tier1_non_upload_staff_management_accessible_when_expired(self, client: AsyncClient):
        """Expired merchant can list and create counter staff (HTTP 200)."""
        store = await seed_store()
        past = utcnow() - timedelta(days=10)
        await set_subscription_in_db(store.merchant_id, status="EXPIRED", expires_at=past)

        # List staff
        list_resp = await client.get("/api/v1/merchants/staff", headers=bearer(store.owner_token))
        assert list_resp.status_code == 200

        # Create staff
        create_payload = {
            "staff_name": "New Cashier",
            "phone": unique_phone(),
            "pin": "123456",
            "can_upload_reels": False,
        }
        create_resp = await client.post("/api/v1/merchants/staff", json=create_payload, headers=bearer(store.owner_token))
        assert create_resp.status_code == 200

    async def test_tier1_non_upload_store_categories_and_public_accessible_when_expired(self, client: AsyncClient):
        """Store categories and public merchant interactions remain fully operational."""
        store = await seed_store()
        past = utcnow() - timedelta(days=10)
        await set_subscription_in_db(store.merchant_id, status="EXPIRED", expires_at=past)

        resp = await client.get("/api/v1/merchants/categories")
        assert resp.status_code == 200
