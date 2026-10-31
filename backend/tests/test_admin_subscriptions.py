"""Integration tests for Admin Subscription Management and Extension Controls (R2)."""
import uuid
from datetime import datetime, timedelta, timezone
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.admin.configs import MODEL_CONFIGS
from app.admin.registry import LABEL_OVERRIDES
from app.core.config import settings
from app.main import app
from tests.e2e_subscriptions.helpers import (
    bearer,
    parse_iso_datetime,
    prepare_schema,
    seed_admin,
    seed_store,
    seed_user,
    set_subscription_in_db,
    utcnow,
)

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture(autouse=True)
async def init_db():
    await prepare_schema()
    yield


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestAdminSubscriptionView:
    """Tests for GET /api/v1/admin/merchants/{id} and merchant list subscriptions."""

    async def test_admin_get_merchant_detail_with_subscription(self, client: AsyncClient):
        _, admin_token = await seed_admin()
        store = await seed_store()
        future = utcnow() + timedelta(days=45)
        await set_subscription_in_db(store.merchant_id, status="ACTIVE", expires_at=future)

        resp = await client.get(f"/api/v1/admin/merchants/{store.merchant_id}", headers=bearer(admin_token))
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["id"] == str(store.merchant_id)
        assert data["subscription_status"] == "ACTIVE"
        assert data["is_subscription_active"] is True
        assert parse_iso_datetime(data["subscription_expires_at"]) is not None

    async def test_admin_get_merchant_security_and_errors(self, client: AsyncClient):
        _, admin_token = await seed_admin()
        _, shopper_token = await seed_user("SHOPPER")
        store = await seed_store()

        # 401 unauthenticated
        assert (await client.get(f"/api/v1/admin/merchants/{store.merchant_id}")).status_code == 401
        # 403 non-admin role
        assert (await client.get(f"/api/v1/admin/merchants/{store.merchant_id}", headers=bearer(shopper_token))).status_code == 403
        # 403 merchant owner
        assert (await client.get(f"/api/v1/admin/merchants/{store.merchant_id}", headers=bearer(store.owner_token))).status_code == 403
        # 404 non-existent
        assert (await client.get(f"/api/v1/admin/merchants/{uuid.uuid4()}", headers=bearer(admin_token))).status_code == 404
        # 422 invalid uuid format
        assert (await client.get("/api/v1/admin/merchants/invalid-uuid", headers=bearer(admin_token))).status_code == 422

    async def test_admin_list_merchants_includes_subscription_fields(self, client: AsyncClient):
        _, admin_token = await seed_admin()
        await seed_store()

        resp = await client.get("/api/v1/admin/merchants", headers=bearer(admin_token))
        assert resp.status_code == 200
        items = resp.json()["data"]
        assert len(items) > 0
        first = items[0]
        assert "subscription_status" in first
        assert "is_subscription_active" in first
        assert "subscription_expires_at" in first


class TestAdminSubscriptionUpdate:
    """Tests for PUT /api/v1/admin/merchants/{id}/subscription."""

    async def test_admin_update_status_and_expiration(self, client: AsyncClient):
        _, admin_token = await seed_admin()
        store = await seed_store()

        # Deactivate
        resp = await client.put(
            f"/api/v1/admin/merchants/{store.merchant_id}/subscription",
            json={"subscription_status": "INACTIVE"},
            headers=bearer(admin_token),
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["subscription_status"] == "INACTIVE"
        assert resp.json()["data"]["is_subscription_active"] is False

        # Reactivate with custom future expiry
        future = utcnow() + timedelta(days=60)
        resp2 = await client.put(
            f"/api/v1/admin/merchants/{store.merchant_id}/subscription",
            json={"subscription_status": "ACTIVE", "subscription_expires_at": future.isoformat()},
            headers=bearer(admin_token),
        )
        assert resp2.status_code == 200
        data2 = resp2.json()["data"]
        assert data2["subscription_status"] == "ACTIVE"
        assert data2["is_subscription_active"] is True
        updated_exp = parse_iso_datetime(data2["subscription_expires_at"])
        assert updated_exp is not None
        assert abs((updated_exp - future).total_seconds()) < 60

    async def test_admin_update_validation_and_auth(self, client: AsyncClient):
        _, admin_token = await seed_admin()
        store = await seed_store()

        # Empty body -> 422
        r_empty = await client.put(
            f"/api/v1/admin/merchants/{store.merchant_id}/subscription",
            json={},
            headers=bearer(admin_token),
        )
        assert r_empty.status_code in (400, 422)

        # Invalid enum -> 422
        r_bad = await client.put(
            f"/api/v1/admin/merchants/{store.merchant_id}/subscription",
            json={"subscription_status": "INVALID_STATE"},
            headers=bearer(admin_token),
        )
        assert r_bad.status_code == 422

        # 403 non-admin
        _, shopper_token = await seed_user("SHOPPER")
        r_unauth = await client.put(
            f"/api/v1/admin/merchants/{store.merchant_id}/subscription",
            json={"subscription_status": "ACTIVE"},
            headers=bearer(shopper_token),
        )
        assert r_unauth.status_code == 403

        # 404 not found
        r_404 = await client.put(
            f"/api/v1/admin/merchants/{uuid.uuid4()}/subscription",
            json={"subscription_status": "ACTIVE"},
            headers=bearer(admin_token),
        )
        assert r_404.status_code == 404


class TestAdminSubscriptionExtend:
    """Tests for POST /api/v1/admin/merchants/{id}/subscription/extend."""

    async def test_admin_extend_defaults_to_90_days(self, client: AsyncClient):
        _, admin_token = await seed_admin()
        store = await seed_store()
        initial_exp = utcnow() + timedelta(days=10)
        await set_subscription_in_db(store.merchant_id, status="ACTIVE", expires_at=initial_exp)

        resp = await client.post(
            f"/api/v1/admin/merchants/{store.merchant_id}/subscription/extend",
            json={},
            headers=bearer(admin_token),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        new_exp = parse_iso_datetime(data["subscription_expires_at"])
        delta_days = (new_exp - initial_exp).total_seconds() / 86400
        assert 89 <= delta_days <= 91

    async def test_admin_extend_custom_days_and_months(self, client: AsyncClient):
        _, admin_token = await seed_admin()
        store = await seed_store()
        cur_exp = utcnow() + timedelta(days=20)
        await set_subscription_in_db(store.merchant_id, status="ACTIVE", expires_at=cur_exp)

        # Extend by 45 days
        resp = await client.post(
            f"/api/v1/admin/merchants/{store.merchant_id}/subscription/extend",
            json={"duration_days": 45},
            headers=bearer(admin_token),
        )
        assert resp.status_code == 200
        exp_45 = parse_iso_datetime(resp.json()["data"]["subscription_expires_at"])
        assert 44 <= (exp_45 - cur_exp).total_seconds() / 86400 <= 46

        # Extend by 2 months (60 days)
        resp2 = await client.post(
            f"/api/v1/admin/merchants/{store.merchant_id}/subscription/extend",
            json={"months": 2},
            headers=bearer(admin_token),
        )
        assert resp2.status_code == 200
        exp_60 = parse_iso_datetime(resp2.json()["data"]["subscription_expires_at"])
        assert 59 <= (exp_60 - exp_45).total_seconds() / 86400 <= 61

    async def test_admin_extend_expired_merchant_from_current_time(self, client: AsyncClient):
        _, admin_token = await seed_admin()
        store = await seed_store()
        past = utcnow() - timedelta(days=40)
        await set_subscription_in_db(store.merchant_id, status="EXPIRED", expires_at=past)

        now = utcnow()
        resp = await client.post(
            f"/api/v1/admin/merchants/{store.merchant_id}/subscription/extend",
            json={"duration_days": 30},
            headers=bearer(admin_token),
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["subscription_status"] == "ACTIVE"
        assert data["is_subscription_active"] is True
        new_exp = parse_iso_datetime(data["subscription_expires_at"])
        assert 29 <= (new_exp - now).total_seconds() / 86400 <= 31

    async def test_admin_extend_validation_and_errors(self, client: AsyncClient):
        _, admin_token = await seed_admin()
        store = await seed_store()

        # Negative days -> 422
        assert (await client.post(
            f"/api/v1/admin/merchants/{store.merchant_id}/subscription/extend",
            json={"duration_days": -15},
            headers=bearer(admin_token),
        )).status_code == 422

        # 403 non-admin
        _, shopper_token = await seed_user("SHOPPER")
        assert (await client.post(
            f"/api/v1/admin/merchants/{store.merchant_id}/subscription/extend",
            json={"duration_days": 30},
            headers=bearer(shopper_token),
        )).status_code == 403

        # 404 not found
        assert (await client.post(
            f"/api/v1/admin/merchants/{uuid.uuid4()}/subscription/extend",
            json={},
            headers=bearer(admin_token),
        )).status_code == 404


class TestAdminPanelWebIntegration:
    """Tests for HTML Admin Panel quick extension and configuration mappings."""

    async def test_admin_web_quick_extend_route(self, client: AsyncClient):
        # Admin sign-in cookie
        login_resp = await client.post(
            "/admin/login",
            data={"identifier": settings.SUPER_ADMIN_IDENTIFIER, "password": settings.SUPER_ADMIN_PASSWORD},
        )
        assert login_resp.status_code == 303

        store = await seed_store()
        initial_exp = utcnow() + timedelta(days=10)
        await set_subscription_in_db(store.merchant_id, status="ACTIVE", expires_at=initial_exp)

        # Quick extension action
        resp = await client.post(
            f"/admin/merchants/{store.merchant_id}/extend-subscription",
            data={"duration_days": "60"},
        )
        assert resp.status_code == 303
        assert f"/admin/merchants/{store.merchant_id}" in resp.headers["location"]

        # Verify detail view reflection via API
        _, admin_token = await seed_admin()
        detail_resp = await client.get(f"/api/v1/admin/merchants/{store.merchant_id}", headers=bearer(admin_token))
        new_exp = parse_iso_datetime(detail_resp.json()["data"]["subscription_expires_at"])
        delta_days = (new_exp - initial_exp).total_seconds() / 86400
        assert 59 <= delta_days <= 61

    async def test_admin_configs_and_registry_labels(self):
        merchant_cfg = next((c for c in MODEL_CONFIGS if c.get("key") == "merchants"), None)
        assert merchant_cfg is not None
        assert "subscription_status" in merchant_cfg["list_columns"]
        assert "subscription_expires_at" in merchant_cfg["list_columns"]
        assert "subscription_status" in merchant_cfg["choices"]
        assert set(merchant_cfg["choices"]["subscription_status"]) == {"ACTIVE", "INACTIVE", "EXPIRED"}

        assert LABEL_OVERRIDES["subscription_status"] == "Subscription Status"
        assert LABEL_OVERRIDES["subscription_start_date"] == "Subscription Starts At"
        assert LABEL_OVERRIDES["subscription_expires_at"] == "Subscription Expires At"
