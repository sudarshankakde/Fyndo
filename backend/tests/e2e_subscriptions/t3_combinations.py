"""Tier 3: Cross-Feature Combinations & Pairwise Interactions."""
from datetime import timedelta
import pytest
from httpx import AsyncClient

from tests.e2e_subscriptions.helpers import (
    assert_error_envelope,
    bearer,
    onboard_merchant_via_api,
    parse_iso_datetime,
    reel_payload,
    seed_admin,
    seed_store,
    seed_user,
    set_subscription_in_db,
    utcnow,
)

pytestmark = pytest.mark.asyncio


class TestTier3CrossFeatureCombinations:
    """Tier 3: Pairwise Combinations Across Subscription Lifecycle & Gating."""

    async def test_tier3_signup_immediate_deactivation_blocks_reel(self, client: AsyncClient):
        """Merchant signs up with 3-month trial, admin immediately deactivates, reel upload is blocked (403)."""
        _, admin_token = await seed_admin()
        _, token, onboard_data = await onboard_merchant_via_api(client, business_name="Immediate Deact Store")
        mid = onboard_data["data"]["id"]

        # Admin deactivates
        update_resp = await client.put(
            f"/api/v1/admin/merchants/{mid}/subscription",
            json={"subscription_status": "INACTIVE"},
            headers=bearer(admin_token),
        )
        assert update_resp.status_code == 200

        # Attempt reel publish
        reel_resp = await client.post("/api/v1/reels", json=reel_payload(), headers=bearer(token))
        assert reel_resp.status_code == 403
        assert_error_envelope(reel_resp.json(), expected_status_code=403, expected_code="HTTP_403")

    async def test_tier3_signup_immediate_deactivation_preserves_profile(self, client: AsyncClient):
        """Merchant signs up, admin deactivates, but profile and business settings remain 200 accessible."""
        _, admin_token = await seed_admin()
        _, token, onboard_data = await onboard_merchant_via_api(client, business_name="Preserve Profile Store")
        mid = onboard_data["data"]["id"]

        await client.put(
            f"/api/v1/admin/merchants/{mid}/subscription",
            json={"subscription_status": "INACTIVE"},
            headers=bearer(admin_token),
        )

        # Profile accessible
        profile_resp = await client.get("/api/v1/merchants/profile", headers=bearer(token))
        assert profile_resp.status_code == 200
        assert profile_resp.json()["data"].get("subscription_status") == "INACTIVE"

    async def test_tier3_expired_merchant_admin_extend_unblocks_reel_immediately(self, client: AsyncClient):
        """Expired merchant blocked on reel publish is immediately unblocked once admin extends."""
        _, admin_token = await seed_admin()
        store = await seed_store()
        await set_subscription_in_db(store.merchant_id, status="EXPIRED", expires_at=utcnow() - timedelta(days=2))

        # First attempt blocked
        r1 = await client.post("/api/v1/reels", json=reel_payload("Blocked Reel"), headers=bearer(store.owner_token))
        assert r1.status_code == 403

        # Admin extends by 90 days
        ext_resp = await client.post(
            f"/api/v1/admin/merchants/{store.merchant_id}/subscription/extend",
            json={"duration_days": 90},
            headers=bearer(admin_token),
        )
        assert ext_resp.status_code == 200

        # Second attempt unblocked
        r2 = await client.post("/api/v1/reels", json=reel_payload("Unblocked Reel"), headers=bearer(store.owner_token))
        assert r2.status_code in (200, 201)

    async def test_tier3_inactive_merchant_admin_activate_unblocks_reel_immediately(self, client: AsyncClient):
        """Inactive merchant is unblocked immediately when admin sets ACTIVE with future date."""
        _, admin_token = await seed_admin()
        store = await seed_store()
        await set_subscription_in_db(store.merchant_id, status="INACTIVE")

        # Blocked
        assert (await client.post("/api/v1/reels", json=reel_payload(), headers=bearer(store.owner_token))).status_code == 403

        # Admin activates
        future = utcnow() + timedelta(days=60)
        await client.put(
            f"/api/v1/admin/merchants/{store.merchant_id}/subscription",
            json={"subscription_status": "ACTIVE", "subscription_expires_at": future.isoformat()},
            headers=bearer(admin_token),
        )

        # Unblocked
        assert (await client.post("/api/v1/reels", json=reel_payload(), headers=bearer(store.owner_token))).status_code in (200, 201)

    async def test_tier3_expired_merchant_cashier_blocked_admin_extend_unblocks_cashier(self, client: AsyncClient):
        """Cashier of expired store blocked from reel upload is unblocked after admin extends store."""
        _, admin_token = await seed_admin()
        store = await seed_store(with_staff=True, can_upload_reels=True)
        await set_subscription_in_db(store.merchant_id, status="EXPIRED", expires_at=utcnow() - timedelta(days=5))

        # Cashier blocked
        r1 = await client.post("/api/v1/reels", json=reel_payload(), headers=bearer(store.staff_token))
        assert r1.status_code == 403

        # Admin extends
        await client.post(
            f"/api/v1/admin/merchants/{store.merchant_id}/subscription/extend",
            json={"duration_days": 30},
            headers=bearer(admin_token),
        )

        # Cashier unblocked
        r2 = await client.post("/api/v1/reels", json=reel_payload("Cashier Reel"), headers=bearer(store.staff_token))
        assert r2.status_code in (200, 201)

    async def test_tier3_active_merchant_admin_updates_expiry_to_past_blocks_upload(self, client: AsyncClient):
        """Admin explicitly shortening expiry to the past blocks subsequent reel creation."""
        _, admin_token = await seed_admin()
        store = await seed_store()
        await set_subscription_in_db(store.merchant_id, status="ACTIVE", expires_at=utcnow() + timedelta(days=30))

        # Can publish
        assert (await client.post("/api/v1/reels", json=reel_payload("Reel 1"), headers=bearer(store.owner_token))).status_code in (200, 201)

        # Admin moves expiry to yesterday
        past = utcnow() - timedelta(days=1)
        await client.put(
            f"/api/v1/admin/merchants/{store.merchant_id}/subscription",
            json={"subscription_status": "ACTIVE", "subscription_expires_at": past.isoformat()},
            headers=bearer(admin_token),
        )

        # Now blocked
        assert (await client.post("/api/v1/reels", json=reel_payload("Reel 2"), headers=bearer(store.owner_token))).status_code == 403

    async def test_tier3_expired_merchant_shopper_follows_and_views_insights(self, client: AsyncClient):
        """Expired merchant receives follows and views insights normally, while upload is gated."""
        store = await seed_store()
        await set_subscription_in_db(store.merchant_id, status="EXPIRED", expires_at=utcnow() - timedelta(days=10))
        _, shopper_token = await seed_user("SHOPPER")

        # Shopper follows store
        follow_resp = await client.post(f"/api/v1/merchants/{store.merchant_id}/follow", headers=bearer(shopper_token))
        assert follow_resp.status_code == 200

        # Merchant views insights
        insights_resp = await client.get("/api/v1/merchants/me/insights", headers=bearer(store.owner_token))
        assert insights_resp.status_code == 200

        # Merchant reel upload is still gated
        reel_resp = await client.post("/api/v1/reels", json=reel_payload(), headers=bearer(store.owner_token))
        assert reel_resp.status_code == 403

    async def test_tier3_admin_inspect_confirm_expired_extend_reinspect_active(self, client: AsyncClient):
        """Admin inspects expired store, extends it, and re-inspects to verify active status."""
        _, admin_token = await seed_admin()
        store = await seed_store()
        await set_subscription_in_db(store.merchant_id, status="EXPIRED", expires_at=utcnow() - timedelta(days=3))

        # Inspect 1: expired
        r1 = await client.get(f"/api/v1/admin/merchants/{store.merchant_id}", headers=bearer(admin_token))
        assert r1.status_code == 200
        assert r1.json()["data"].get("is_subscription_active") is False

        # Extend
        await client.post(
            f"/api/v1/admin/merchants/{store.merchant_id}/subscription/extend",
            json={"duration_days": 60},
            headers=bearer(admin_token),
        )

        # Inspect 2: active
        r2 = await client.get(f"/api/v1/admin/merchants/{store.merchant_id}", headers=bearer(admin_token))
        assert r2.status_code == 200
        assert r2.json()["data"].get("is_subscription_active") is True

    async def test_tier3_two_merchants_one_active_one_expired_isolation(self, client: AsyncClient):
        """Active store publishes reel successfully while concurrently expired store is blocked."""
        active_store = await seed_store()
        await set_subscription_in_db(active_store.merchant_id, status="ACTIVE", expires_at=utcnow() + timedelta(days=30))

        expired_store = await seed_store()
        await set_subscription_in_db(expired_store.merchant_id, status="EXPIRED", expires_at=utcnow() - timedelta(days=5))

        r_active = await client.post("/api/v1/reels", json=reel_payload("Active"), headers=bearer(active_store.owner_token))
        r_expired = await client.post("/api/v1/reels", json=reel_payload("Expired"), headers=bearer(expired_store.owner_token))

        assert r_active.status_code in (200, 201)
        assert r_expired.status_code == 403

    async def test_tier3_cashier_permission_toggle_under_active_vs_expired_subscription(self, client: AsyncClient):
        """Owner granting upload permission to cashier does not bypass store-level subscription expiry."""
        store = await seed_store(with_staff=True, can_upload_reels=False)
        await set_subscription_in_db(store.merchant_id, status="EXPIRED", expires_at=utcnow() - timedelta(days=4))

        # Owner grants cashier upload permission
        perm_resp = await client.patch(
            f"/api/v1/merchants/staff/{store.staff_id}/permissions",
            json={"can_upload_reels": True},
            headers=bearer(store.owner_token),
        )
        assert perm_resp.status_code == 200

        # Cashier still blocked due to store subscription expiry
        reel_resp = await client.post("/api/v1/reels", json=reel_payload(), headers=bearer(store.staff_token))
        assert reel_resp.status_code == 403

    async def test_tier3_coupon_analytics_accessible_while_reel_creation_blocked(self, client: AsyncClient):
        """Merchant can access /merchants/analytics while reel publishing is blocked."""
        store = await seed_store()
        await set_subscription_in_db(store.merchant_id, status="EXPIRED", expires_at=utcnow() - timedelta(days=7))

        analytics_resp = await client.get("/api/v1/merchants/analytics", headers=bearer(store.owner_token))
        assert analytics_resp.status_code == 200

        reel_resp = await client.post("/api/v1/reels", json=reel_payload(), headers=bearer(store.owner_token))
        assert reel_resp.status_code == 403
