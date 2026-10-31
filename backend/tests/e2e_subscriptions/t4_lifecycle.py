"""Tier 4: Real-World Merchant Subscription Lifecycle Scenarios."""
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


class TestTier4RealWorldScenarios:
    """Tier 4: Comprehensive End-to-End Real-World Application Workflows."""

    async def test_tier4_full_lifecycle_onboard_publish_expire_gate_extend_resume(self, client: AsyncClient):
        """Full lifecycle: Onboarding -> Reel publishing -> Expiration -> Gating -> Admin Extension -> Reel Publishing Resumes."""
        _, admin_token = await seed_admin("Ops Admin")

        # Step 1: New merchant onboards with 3-month free trial
        _, token, onboard_data = await onboard_merchant_via_api(client, business_name="Grand Bazaar")
        assert onboard_data.get("success") is True
        mid = onboard_data["data"]["id"]
        assert onboard_data["data"].get("subscription_status") == "ACTIVE"
        assert onboard_data["data"].get("is_subscription_active") is True

        # Step 2: Merchant publishes initial showcase reel
        r_init = await client.post("/api/v1/reels", json=reel_payload("Welcome Reel"), headers=bearer(token))
        assert r_init.status_code in (200, 201), r_init.text

        # Step 3: Trial period elapses into expired state
        past = utcnow() - timedelta(days=5)
        await set_subscription_in_db(mid, status="EXPIRED", expires_at=past)

        # Step 4: Merchant dashboard, profile, and analytics remain 100% accessible
        p_resp = await client.get("/api/v1/merchants/profile", headers=bearer(token))
        assert p_resp.status_code == 200
        assert p_resp.json()["data"].get("is_subscription_active") is False

        i_resp = await client.get("/api/v1/merchants/me/insights", headers=bearer(token))
        assert i_resp.status_code == 200

        # Step 5: Merchant attempts to publish a new seasonal reel -> Gated with HTTP 403
        r_gated = await client.post("/api/v1/reels", json=reel_payload("Seasonal Sale"), headers=bearer(token))
        assert r_gated.status_code == 403
        assert_error_envelope(r_gated.json(), expected_status_code=403, expected_code="HTTP_403")

        # Step 6: Admin inspects merchant account in admin plane and extends by 90 days
        inspect = await client.get(f"/api/v1/admin/merchants/{mid}", headers=bearer(admin_token))
        assert inspect.status_code == 200
        assert inspect.json()["data"].get("is_subscription_active") is False

        ext_resp = await client.post(
            f"/api/v1/admin/merchants/{mid}/subscription/extend",
            json={"duration_days": 90},
            headers=bearer(admin_token),
        )
        assert ext_resp.status_code == 200
        assert ext_resp.json()["data"].get("is_subscription_active") is True

        # Step 7: Merchant retries publishing seasonal reel -> Succeeds immediately
        r_resumed = await client.post("/api/v1/reels", json=reel_payload("Seasonal Sale"), headers=bearer(token))
        assert r_resumed.status_code in (200, 201)

    async def test_tier4_deactivation_investigation_and_reactivation_workflow(self, client: AsyncClient):
        """Admin suspends merchant for review, merchant adjusts profile, admin reactivates."""
        _, admin_token = await seed_admin()
        store = await seed_store()

        # Admin temporarily marks INACTIVE for compliance review
        await client.put(
            f"/api/v1/admin/merchants/{store.merchant_id}/subscription",
            json={"subscription_status": "INACTIVE"},
            headers=bearer(admin_token),
        )

        # Upload is blocked
        r_blocked = await client.post("/api/v1/reels", json=reel_payload(), headers=bearer(store.owner_token))
        assert r_blocked.status_code == 403

        # Merchant updates store profile to meet guidelines
        upd_resp = await client.patch(
            "/api/v1/merchants/profile",
            json={"description": "Updated compliant business description"},
            headers=bearer(store.owner_token),
        )
        assert upd_resp.status_code == 200

        # Admin approves and reactivates subscription
        future = utcnow() + timedelta(days=60)
        reac_resp = await client.put(
            f"/api/v1/admin/merchants/{store.merchant_id}/subscription",
            json={"subscription_status": "ACTIVE", "subscription_expires_at": future.isoformat()},
            headers=bearer(admin_token),
        )
        assert reac_resp.status_code == 200

        # Upload succeeds
        r_ok = await client.post("/api/v1/reels", json=reel_payload("Compliant Reel"), headers=bearer(store.owner_token))
        assert r_ok.status_code in (200, 201)

    async def test_tier4_multi_staff_store_operations_during_subscription_lapse(self, client: AsyncClient):
        """Store with counter cashier: Cashier continues viewing store info while upload is gated; resumes upon extension."""
        _, admin_token = await seed_admin()
        store = await seed_store(with_staff=True, can_upload_reels=True)
        await set_subscription_in_db(store.merchant_id, status="EXPIRED", expires_at=utcnow() - timedelta(days=1))

        # Cashier profile access works
        p_resp = await client.get("/api/v1/merchants/profile", headers=bearer(store.staff_token))
        assert p_resp.status_code == 200

        # Cashier upload fails (403)
        c_reel = await client.post("/api/v1/reels", json=reel_payload(), headers=bearer(store.staff_token))
        assert c_reel.status_code == 403

        # Admin extends subscription by 60 days
        await client.post(
            f"/api/v1/admin/merchants/{store.merchant_id}/subscription/extend",
            json={"duration_days": 60},
            headers=bearer(admin_token),
        )

        # Cashier upload now succeeds
        c_reel2 = await client.post("/api/v1/reels", json=reel_payload("Cashier Special"), headers=bearer(store.staff_token))
        assert c_reel2.status_code in (200, 201)

    async def test_tier4_consecutive_admin_extensions_cumulative_timeline(self, client: AsyncClient):
        """Consecutive extensions accumulate properly on an active subscription."""
        _, admin_token = await seed_admin()
        store = await seed_store()
        initial_exp = utcnow() + timedelta(days=90)
        await set_subscription_in_db(store.merchant_id, status="ACTIVE", expires_at=initial_exp)

        # First extension: +30 days
        ext1 = await client.post(
            f"/api/v1/admin/merchants/{store.merchant_id}/subscription/extend",
            json={"duration_days": 30},
            headers=bearer(admin_token),
        )
        assert ext1.status_code == 200
        exp1 = parse_iso_datetime(ext1.json()["data"].get("subscription_expires_at"))
        delta1 = (exp1 - initial_exp).total_seconds() / 86400
        assert 29.0 <= delta1 <= 31.0

        # Second extension: +60 days
        ext2 = await client.post(
            f"/api/v1/admin/merchants/{store.merchant_id}/subscription/extend",
            json={"duration_days": 60},
            headers=bearer(admin_token),
        )
        assert ext2.status_code == 200
        exp2 = parse_iso_datetime(ext2.json()["data"].get("subscription_expires_at"))
        delta2 = (exp2 - exp1).total_seconds() / 86400
        assert 59.0 <= delta2 <= 61.0

        # Total cumulative extension is ~90 days beyond initial
        assert 88.0 <= (exp2 - initial_exp).total_seconds() / 86400 <= 92.0

    async def test_tier4_long_term_expired_store_business_continuity(self, client: AsyncClient):
        """Store expired for 60 days maintains normal operations for customer interaction and profile maintenance."""
        store = await seed_store()
        await set_subscription_in_db(store.merchant_id, status="EXPIRED", expires_at=utcnow() - timedelta(days=60))
        _, shopper_token = await seed_user("SHOPPER")

        # Shopper follow
        f_resp = await client.post(f"/api/v1/merchants/{store.merchant_id}/follow", headers=bearer(shopper_token))
        assert f_resp.status_code == 200

        # Merchant analytics
        a_resp = await client.get("/api/v1/merchants/analytics", headers=bearer(store.owner_token))
        assert a_resp.status_code == 200

        # Merchant updates settings
        s_resp = await client.patch(
            "/api/v1/merchants/profile",
            json={"website": "https://grandbazaar.example.com"},
            headers=bearer(store.owner_token),
        )
        assert s_resp.status_code == 200

        # Reel publishing remains strictly gated
        r_resp = await client.post("/api/v1/reels", json=reel_payload(), headers=bearer(store.owner_token))
        assert r_resp.status_code == 403
