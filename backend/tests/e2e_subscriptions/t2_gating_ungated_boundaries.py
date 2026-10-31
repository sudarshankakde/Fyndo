"""Tier 2 - Boundaries: Content Gating & Non-Upload Preservation."""
from datetime import timedelta
import pytest
from httpx import AsyncClient

from tests.e2e_subscriptions.helpers import (
    assert_error_envelope,
    bearer,
    reel_payload,
    seed_admin,
    seed_store,
    seed_user,
    set_subscription_in_db,
    unique_phone,
    utcnow,
)

pytestmark = pytest.mark.asyncio


class TestTier2GatingBoundaries:
    """Tier 2: Boundaries for Reel Content Upload Gating."""

    async def test_tier2_gating_boundary_status_transition_mid_lifecycle_blocks(self, client: AsyncClient):
        """Active merchant can publish reel, but after subscription lapses subsequent upload is blocked."""
        store = await seed_store()
        future = utcnow() + timedelta(days=1)
        await set_subscription_in_db(store.merchant_id, status="ACTIVE", expires_at=future)

        # First reel succeeds
        r1 = await client.post("/api/v1/reels", json=reel_payload("First Reel"), headers=bearer(store.owner_token))
        assert r1.status_code in (200, 201)

        # Time passes -> subscription expires
        past = utcnow() - timedelta(minutes=5)
        await set_subscription_in_db(store.merchant_id, status="EXPIRED", expires_at=past)

        # Second reel fails with 403
        r2 = await client.post("/api/v1/reels", json=reel_payload("Second Reel"), headers=bearer(store.owner_token))
        assert r2.status_code == 403
        assert_error_envelope(r2.json(), expected_status_code=403, expected_code="HTTP_403")

    async def test_tier2_gating_boundary_cashier_without_upload_permission_and_expired(self, client: AsyncClient):
        """Cashier without upload permission on an expired store receives 403 without 500 error."""
        store = await seed_store(with_staff=True, can_upload_reels=False)
        past = utcnow() - timedelta(days=3)
        await set_subscription_in_db(store.merchant_id, status="EXPIRED", expires_at=past)

        resp = await client.post("/api/v1/reels", json=reel_payload(), headers=bearer(store.staff_token))
        assert resp.status_code == 403

    async def test_tier2_gating_boundary_reactivation_immediately_allows_upload(self, client: AsyncClient):
        """Reactivating an expired merchant immediately allows them to publish reels."""
        store = await seed_store()
        past = utcnow() - timedelta(days=2)
        await set_subscription_in_db(store.merchant_id, status="EXPIRED", expires_at=past)

        # Blocked
        blocked = await client.post("/api/v1/reels", json=reel_payload(), headers=bearer(store.owner_token))
        assert blocked.status_code == 403

        # Admin activates / extends
        future = utcnow() + timedelta(days=30)
        await set_subscription_in_db(store.merchant_id, status="ACTIVE", expires_at=future)

        # Now allowed
        allowed = await client.post("/api/v1/reels", json=reel_payload("After Reactivation"), headers=bearer(store.owner_token))
        assert allowed.status_code in (200, 201)

    async def test_tier2_gating_boundary_inactive_vs_expired_both_return_403(self, client: AsyncClient):
        """Both INACTIVE status and EXPIRED status consistently trigger 403 gating."""
        store_inactive = await seed_store()
        await set_subscription_in_db(store_inactive.merchant_id, status="INACTIVE")
        resp1 = await client.post("/api/v1/reels", json=reel_payload(), headers=bearer(store_inactive.owner_token))
        assert resp1.status_code == 403

        store_expired = await seed_store()
        await set_subscription_in_db(store_expired.merchant_id, status="EXPIRED", expires_at=utcnow() - timedelta(hours=1))
        resp2 = await client.post("/api/v1/reels", json=reel_payload(), headers=bearer(store_expired.owner_token))
        assert resp2.status_code == 403

    async def test_tier2_gating_boundary_malformed_reel_payload_on_expired_merchant(self, client: AsyncClient):
        """Expired merchant uploading an incomplete payload still receives an error without internal server error."""
        store = await seed_store()
        await set_subscription_in_db(store.merchant_id, status="EXPIRED", expires_at=utcnow() - timedelta(days=2))

        resp = await client.post("/api/v1/reels", json={}, headers=bearer(store.owner_token))
        assert resp.status_code in (400, 403, 422)

    async def test_tier2_gating_boundary_kyc_pending_vs_subscription_expired_priority(self, client: AsyncClient):
        """Store with pending KYC and expired subscription fails authorization cleanly."""
        from tests.feature_helpers import set_auto_approve_kyc
        await set_auto_approve_kyc(False)
        try:
            store = await seed_store()
            await set_subscription_in_db(store.merchant_id, status="EXPIRED", expires_at=utcnow() - timedelta(days=2))

            resp = await client.post("/api/v1/reels", json=reel_payload(), headers=bearer(store.owner_token))
            assert resp.status_code == 403
        finally:
            await set_auto_approve_kyc(True)


class TestTier2NonUploadBoundaries:
    """Tier 2: Boundaries for Ungated Operations on Inactive / Expired Accounts."""

    async def test_tier2_non_upload_boundary_expired_merchant_update_business_hours(self, client: AsyncClient):
        """Updating store hours succeeds even when subscription is expired."""
        store = await seed_store()
        await set_subscription_in_db(store.merchant_id, status="EXPIRED", expires_at=utcnow() - timedelta(days=5))

        payload = {"business_hours": "11:00 AM - 11:00 PM"}
        resp = await client.patch("/api/v1/merchants/profile", json=payload, headers=bearer(store.owner_token))
        assert resp.status_code == 200
        assert resp.json()["data"].get("business_hours") == payload["business_hours"]

    async def test_tier2_non_upload_boundary_expired_merchant_cover_and_logo_update(self, client: AsyncClient):
        """Updating logo and cover photo succeeds on expired merchant."""
        store = await seed_store()
        await set_subscription_in_db(store.merchant_id, status="EXPIRED", expires_at=utcnow() - timedelta(days=5))

        payload = {
            "cover_url": "https://res.cloudinary.com/fyndo/image/upload/new_cover.webp",
            "logo_url": "https://res.cloudinary.com/fyndo/image/upload/new_logo.webp",
        }
        resp = await client.patch("/api/v1/merchants/profile", json=payload, headers=bearer(store.owner_token))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data.get("cover_url") == payload["cover_url"]
        assert data.get("logo_url") == payload["logo_url"]

    async def test_tier2_non_upload_boundary_expired_merchant_staff_creation(self, client: AsyncClient):
        """Creating cashier staff succeeds on expired merchant."""
        store = await seed_store()
        await set_subscription_in_db(store.merchant_id, status="EXPIRED", expires_at=utcnow() - timedelta(days=5))

        payload = {
            "staff_name": "Evening Cashier",
            "phone": unique_phone(),
            "pin": "654321",
            "can_upload_reels": False,
        }
        resp = await client.post("/api/v1/merchants/staff", json=payload, headers=bearer(store.owner_token))
        assert resp.status_code == 200

    async def test_tier2_non_upload_boundary_expired_merchant_staff_permission_toggle(self, client: AsyncClient):
        """Store owner can update cashier permissions on expired merchant."""
        store = await seed_store(with_staff=True, can_upload_reels=False)
        await set_subscription_in_db(store.merchant_id, status="EXPIRED", expires_at=utcnow() - timedelta(days=5))

        payload = {"can_upload_reels": True, "can_manage_content": True}
        resp = await client.patch(
            f"/api/v1/merchants/staff/{store.staff_id}/permissions",
            json=payload,
            headers=bearer(store.owner_token),
        )
        assert resp.status_code == 200

    async def test_tier2_non_upload_boundary_expired_merchant_analytics_endpoint(self, client: AsyncClient):
        """GET /api/v1/merchants/analytics returns 200 on expired merchant."""
        store = await seed_store()
        await set_subscription_in_db(store.merchant_id, status="EXPIRED", expires_at=utcnow() - timedelta(days=5))

        resp = await client.get("/api/v1/merchants/analytics", headers=bearer(store.owner_token))
        assert resp.status_code == 200

    async def test_tier2_non_upload_boundary_expired_merchant_shopper_follows(self, client: AsyncClient):
        """Shopper can follow an expired store without impediment."""
        store = await seed_store()
        await set_subscription_in_db(store.merchant_id, status="EXPIRED", expires_at=utcnow() - timedelta(days=5))
        _, shopper_token = await seed_user("SHOPPER", "Follower Shopper")

        resp = await client.post(f"/api/v1/merchants/{store.merchant_id}/follow", headers=bearer(shopper_token))
        assert resp.status_code == 200
        assert resp.json()["data"].get("is_following") is True
