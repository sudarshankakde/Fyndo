"""Tier 1 - Features 3, 4, 5: Admin View, Update & Extend Subscription APIs."""
import uuid
from datetime import timedelta
import pytest
from httpx import AsyncClient

from tests.e2e_subscriptions.helpers import (
    bearer,
    parse_iso_datetime,
    seed_admin,
    seed_store,
    seed_user,
    set_subscription_in_db,
    utcnow,
)

pytestmark = pytest.mark.asyncio


class TestTier1AdminView:
    """Tier 1: Feature 3 - Admin View Subscription & Timestamps."""

    async def test_tier1_admin_view_merchant_subscription_details(self, client: AsyncClient):
        """Super Admin can retrieve merchant detail with subscription fields."""
        _, admin_token = await seed_admin()
        store = await seed_store()
        future = utcnow() + timedelta(days=45)
        await set_subscription_in_db(store.merchant_id, status="ACTIVE", expires_at=future)

        resp = await client.get(f"/api/v1/admin/merchants/{store.merchant_id}", headers=bearer(admin_token))
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data.get("subscription_status") == "ACTIVE"
        assert data.get("is_subscription_active") is True
        assert parse_iso_datetime(data.get("subscription_expires_at")) is not None

    async def test_tier1_admin_view_merchant_unauthorized_for_shopper(self, client: AsyncClient):
        """Shopper role receives 403 Forbidden attempting to access admin merchant endpoint."""
        _, shopper_token = await seed_user("SHOPPER", "Regular Shopper")
        store = await seed_store()

        resp = await client.get(f"/api/v1/admin/merchants/{store.merchant_id}", headers=bearer(shopper_token))
        assert resp.status_code == 403

    async def test_tier1_admin_view_merchant_unauthenticated(self, client: AsyncClient):
        """Unauthenticated caller receives 401 Unauthorized accessing admin merchant endpoint."""
        store = await seed_store()
        resp = await client.get(f"/api/v1/admin/merchants/{store.merchant_id}")
        assert resp.status_code == 401

    async def test_tier1_admin_view_merchant_not_found(self, client: AsyncClient):
        """Admin requesting a non-existent merchant UUID receives 404 Not Found."""
        _, admin_token = await seed_admin()
        random_id = uuid.uuid4()

        resp = await client.get(f"/api/v1/admin/merchants/{random_id}", headers=bearer(admin_token))
        assert resp.status_code == 404

    async def test_tier1_admin_list_merchants_includes_subscription_columns(self, client: AsyncClient):
        """GET /api/v1/admin/merchants list includes subscription status for each store."""
        _, admin_token = await seed_admin()
        await seed_store()

        resp = await client.get("/api/v1/admin/merchants", headers=bearer(admin_token))
        assert resp.status_code == 200
        items = resp.json()["data"]
        assert isinstance(items, list) and len(items) > 0
        assert "subscription_status" in items[0]


class TestTier1AdminUpdate:
    """Tier 1: Feature 4 - Admin Update & Activate Subscription."""

    async def test_tier1_admin_update_activate_subscription(self, client: AsyncClient):
        """Admin can activate an inactive subscription via PUT."""
        _, admin_token = await seed_admin()
        store = await seed_store()
        await set_subscription_in_db(store.merchant_id, status="INACTIVE")

        future = utcnow() + timedelta(days=60)
        payload = {
            "subscription_status": "ACTIVE",
            "subscription_expires_at": future.isoformat(),
        }
        resp = await client.put(
            f"/api/v1/admin/merchants/{store.merchant_id}/subscription",
            json=payload,
            headers=bearer(admin_token),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data.get("subscription_status") == "ACTIVE"
        assert data.get("is_subscription_active") is True

    async def test_tier1_admin_update_custom_expiry_date(self, client: AsyncClient):
        """Admin can set a custom expiration timestamp via PUT."""
        _, admin_token = await seed_admin()
        store = await seed_store()
        custom_date = utcnow() + timedelta(days=120)

        payload = {"subscription_status": "ACTIVE", "subscription_expires_at": custom_date.isoformat()}
        resp = await client.put(
            f"/api/v1/admin/merchants/{store.merchant_id}/subscription",
            json=payload,
            headers=bearer(admin_token),
        )
        assert resp.status_code == 200
        updated = parse_iso_datetime(resp.json()["data"].get("subscription_expires_at"))
        assert updated is not None
        assert abs((updated - custom_date).total_seconds()) < 60

    async def test_tier1_admin_update_deactivate_subscription(self, client: AsyncClient):
        """Admin can set subscription_status to INACTIVE via PUT."""
        _, admin_token = await seed_admin()
        store = await seed_store()

        payload = {"subscription_status": "INACTIVE"}
        resp = await client.put(
            f"/api/v1/admin/merchants/{store.merchant_id}/subscription",
            json=payload,
            headers=bearer(admin_token),
        )
        assert resp.status_code == 200
        assert resp.json()["data"].get("subscription_status") == "INACTIVE"
        assert resp.json()["data"].get("is_subscription_active") is False

    async def test_tier1_admin_update_unauthorized_for_merchant(self, client: AsyncClient):
        """Merchant owner cannot call the admin subscription update endpoint."""
        store = await seed_store()
        payload = {"subscription_status": "ACTIVE"}

        resp = await client.put(
            f"/api/v1/admin/merchants/{store.merchant_id}/subscription",
            json=payload,
            headers=bearer(store.owner_token),
        )
        assert resp.status_code == 403

    async def test_tier1_admin_update_not_found(self, client: AsyncClient):
        """Admin updating subscription for non-existent merchant ID receives 404."""
        _, admin_token = await seed_admin()
        payload = {"subscription_status": "ACTIVE"}

        resp = await client.put(
            f"/api/v1/admin/merchants/{uuid.uuid4()}/subscription",
            json=payload,
            headers=bearer(admin_token),
        )
        assert resp.status_code == 404


class TestTier1AdminExtend:
    """Tier 1: Feature 5 - Admin Extend Subscription (Duration / Custom)."""

    async def test_tier1_admin_extend_subscription_default_90_days(self, client: AsyncClient):
        """Admin extend endpoint defaults to 90-day extension when no body provided."""
        _, admin_token = await seed_admin()
        store = await seed_store()
        current_exp = utcnow() + timedelta(days=10)
        await set_subscription_in_db(store.merchant_id, status="ACTIVE", expires_at=current_exp)

        resp = await client.post(
            f"/api/v1/admin/merchants/{store.merchant_id}/subscription/extend",
            json={},
            headers=bearer(admin_token),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        new_exp = parse_iso_datetime(data.get("subscription_expires_at"))
        assert new_exp is not None
        delta = (new_exp - current_exp).total_seconds() / 86400
        assert 89 <= delta <= 91

    async def test_tier1_admin_extend_subscription_custom_duration_days(self, client: AsyncClient):
        """Admin can specify custom duration_days (e.g. 45 days)."""
        _, admin_token = await seed_admin()
        store = await seed_store()
        current_exp = utcnow() + timedelta(days=5)
        await set_subscription_in_db(store.merchant_id, status="ACTIVE", expires_at=current_exp)

        resp = await client.post(
            f"/api/v1/admin/merchants/{store.merchant_id}/subscription/extend",
            json={"duration_days": 45},
            headers=bearer(admin_token),
        )
        assert resp.status_code == 200
        new_exp = parse_iso_datetime(resp.json()["data"].get("subscription_expires_at"))
        assert new_exp is not None
        delta = (new_exp - current_exp).total_seconds() / 86400
        assert 44 <= delta <= 46

    async def test_tier1_admin_extend_subscription_months_parameter(self, client: AsyncClient):
        """Admin can specify months parameter (e.g. months=3)."""
        _, admin_token = await seed_admin()
        store = await seed_store()
        current_exp = utcnow() + timedelta(days=15)
        await set_subscription_in_db(store.merchant_id, status="ACTIVE", expires_at=current_exp)

        resp = await client.post(
            f"/api/v1/admin/merchants/{store.merchant_id}/subscription/extend",
            json={"months": 3},
            headers=bearer(admin_token),
        )
        assert resp.status_code == 200
        new_exp = parse_iso_datetime(resp.json()["data"].get("subscription_expires_at"))
        assert new_exp is not None
        delta = (new_exp - current_exp).total_seconds() / 86400
        assert 89 <= delta <= 93

    async def test_tier1_admin_extend_expired_subscription_from_now(self, client: AsyncClient):
        """Extending an already expired subscription sets the new expiry relative to now."""
        _, admin_token = await seed_admin()
        store = await seed_store()
        past_exp = utcnow() - timedelta(days=30)
        await set_subscription_in_db(store.merchant_id, status="EXPIRED", expires_at=past_exp)

        now = utcnow()
        resp = await client.post(
            f"/api/v1/admin/merchants/{store.merchant_id}/subscription/extend",
            json={"duration_days": 30},
            headers=bearer(admin_token),
        )
        assert resp.status_code == 200
        new_exp = parse_iso_datetime(resp.json()["data"].get("subscription_expires_at"))
        assert new_exp is not None
        delta = (new_exp - now).total_seconds() / 86400
        assert 29 <= delta <= 31

    async def test_tier1_admin_extend_unauthorized_shopper(self, client: AsyncClient):
        """Non-admin user cannot extend merchant subscriptions."""
        _, shopper_token = await seed_user("SHOPPER")
        store = await seed_store()

        resp = await client.post(
            f"/api/v1/admin/merchants/{store.merchant_id}/subscription/extend",
            json={"duration_days": 90},
            headers=bearer(shopper_token),
        )
        assert resp.status_code == 403
