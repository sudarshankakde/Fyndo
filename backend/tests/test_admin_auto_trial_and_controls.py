"""Tests for Auto-Trial Duration and Admin Panel Subscription/KYC Management Controls."""
import uuid
from datetime import datetime, timedelta, timezone
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.core.database import async_session_factory
from app.main import app
from app.models import KycStatus, Merchant, SubscriptionStatus
from app.models.system_settings import AUTO_TRIAL_DURATION_DAYS, AUTO_TRIAL_ENABLED
from app.services.settings_service import (
    get_auto_trial_duration_days,
    is_auto_trial_enabled,
    set_setting,
)
from tests.e2e_subscriptions.helpers import (
    bearer,
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
    from sqlalchemy import delete
    from app.models.system_settings import SystemSetting
    async with async_session_factory() as db:
        await db.execute(delete(SystemSetting))
        await db.commit()
    yield


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestAutoTrialSettings:
    """Verifies system settings defaults, services, and REST API updates."""

    async def test_auto_trial_defaults_and_helpers(self):
        async with async_session_factory() as db:
            assert await is_auto_trial_enabled(db) is True
            assert await get_auto_trial_duration_days(db) == 90

            await set_setting(db, AUTO_TRIAL_ENABLED, False)
            await set_setting(db, AUTO_TRIAL_DURATION_DAYS, 60)
            await db.commit()

            assert await is_auto_trial_enabled(db) is False
            assert await get_auto_trial_duration_days(db) == 60

    async def test_admin_settings_api_patch_and_get(self, client: AsyncClient):
        _, admin_token = await seed_admin()

        patch_res = await client.patch(
            "/api/v1/admin/settings",
            json={"auto_trial_enabled": True, "auto_trial_duration_days": 180},
            headers=bearer(admin_token),
        )
        assert patch_res.status_code == 200, patch_res.text

        get_res = await client.get("/api/v1/admin/settings", headers=bearer(admin_token))
        assert get_res.status_code == 200
        settings_map = {item["key"]: item["value"] for item in get_res.json()["data"]}
        assert settings_map.get("auto_trial_enabled") is True
        assert settings_map.get("auto_trial_duration_days") == 180


class TestMerchantOnboardingAutoTrialDuration:
    """Verifies merchant onboarding respects dynamic auto-trial settings."""

    async def test_onboard_with_custom_trial_duration(self, client: AsyncClient):
        async with async_session_factory() as db:
            await set_setting(db, AUTO_TRIAL_ENABLED, True)
            await set_setting(db, AUTO_TRIAL_DURATION_DAYS, 45)
            await db.commit()

        user_id, user_token = await seed_user("SHOPPER")
        onboard_payload = {
            "business_name": "Dynamic Trial Store",
            "sector": "Retail",
            "address_text": "123 Market St",
            "city": "Pune",
            "latitude": 18.5204,
            "longitude": 73.8567,
            "kyc_doc_url": "https://example.com/kyc1.pdf",
        }
        res = await client.post("/api/v1/merchants/onboard", json=onboard_payload, headers=bearer(user_token))
        assert res.status_code == 200, res.text
        data = res.json()["data"]

        assert data["subscription_status"] == "ACTIVE"
        exp = datetime.fromisoformat(data["subscription_expires_at"])
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        diff_days = (exp - datetime.now(timezone.utc)).total_seconds() / 86400
        assert 44 <= diff_days <= 46

    async def test_onboard_when_auto_trial_disabled(self, client: AsyncClient):
        async with async_session_factory() as db:
            await set_setting(db, AUTO_TRIAL_ENABLED, False)
            await db.commit()

        user_id, user_token = await seed_user("SHOPPER")
        onboard_payload = {
            "business_name": "No Trial Store",
            "sector": "Services",
            "address_text": "456 Tech Park",
            "city": "Mumbai",
            "latitude": 19.0760,
            "longitude": 72.8777,
            "kyc_doc_url": "https://example.com/kyc2.pdf",
        }
        res = await client.post("/api/v1/merchants/onboard", json=onboard_payload, headers=bearer(user_token))
        assert res.status_code == 200, res.text
        data = res.json()["data"]

        assert data["subscription_status"] == "INACTIVE"
        assert data["subscription_expires_at"] is None


class TestAdminPanelWebSubscriptionControls:
    """Verifies HTML Admin Panel actions for auto trial and merchant subscription/KYC."""

    async def _login_admin(self, client: AsyncClient):
        res = await client.post(
            "/admin/login",
            data={"identifier": settings.SUPER_ADMIN_IDENTIFIER, "password": settings.SUPER_ADMIN_PASSWORD},
        )
        assert res.status_code == 303

    async def test_admin_settings_auto_trial_form(self, client: AsyncClient):
        await self._login_admin(client)
        resp = await client.post(
            "/admin/settings/auto-trial",
            data={"enabled": "on", "duration_days": "120"},
        )
        assert resp.status_code == 303
        assert "/admin/?ok=" in resp.headers["location"]

        async with async_session_factory() as db:
            assert await is_auto_trial_enabled(db) is True
            assert await get_auto_trial_duration_days(db) == 120

    async def test_admin_merchant_subscription_activate(self, client: AsyncClient):
        await self._login_admin(client)
        store = await seed_store()
        await set_subscription_in_db(store.merchant_id, status="INACTIVE", expires_at=None)

        resp = await client.post(
            f"/admin/merchants/{store.merchant_id}/subscription/activate",
            data={"duration_days": "60"},
        )
        assert resp.status_code == 303

        async with async_session_factory() as db:
            m = await db.get(Merchant, store.merchant_id)
            assert m.subscription_status == SubscriptionStatus.ACTIVE
            assert m.subscription_expires_at is not None
            days_left = (m.subscription_expires_at - datetime.now(timezone.utc)).total_seconds() / 86400
            assert 59 <= days_left <= 61

    async def test_admin_merchant_subscription_extend(self, client: AsyncClient):
        await self._login_admin(client)
        store = await seed_store()
        cur_exp = datetime.now(timezone.utc) + timedelta(days=10)
        await set_subscription_in_db(store.merchant_id, status="ACTIVE", expires_at=cur_exp)

        resp = await client.post(
            f"/admin/merchants/{store.merchant_id}/subscription/extend",
            data={"duration_days": "30"},
        )
        assert resp.status_code == 303

        async with async_session_factory() as db:
            m = await db.get(Merchant, store.merchant_id)
            days_diff = (m.subscription_expires_at - cur_exp).total_seconds() / 86400
            assert 29 <= days_diff <= 31

    async def test_admin_merchant_subscription_set_expiry(self, client: AsyncClient):
        await self._login_admin(client)
        store = await seed_store()

        resp = await client.post(
            f"/admin/merchants/{store.merchant_id}/subscription/set-expiry",
            data={"expiry_date": "2029-06-30"},
        )
        assert resp.status_code == 303

        async with async_session_factory() as db:
            m = await db.get(Merchant, store.merchant_id)
            assert m.subscription_status == SubscriptionStatus.ACTIVE
            assert m.subscription_expires_at.year == 2029
            assert m.subscription_expires_at.month == 6
            assert m.subscription_expires_at.day == 30

    async def test_admin_merchant_subscription_deactivate(self, client: AsyncClient):
        await self._login_admin(client)
        store = await seed_store()
        await set_subscription_in_db(store.merchant_id, status="ACTIVE", expires_at=datetime.now(timezone.utc) + timedelta(days=30))

        resp = await client.post(f"/admin/merchants/{store.merchant_id}/subscription/deactivate")
        assert resp.status_code == 303

        async with async_session_factory() as db:
            m = await db.get(Merchant, store.merchant_id)
            assert m.subscription_status == SubscriptionStatus.INACTIVE

    async def test_admin_merchant_kyc_approve_and_reject(self, client: AsyncClient):
        await self._login_admin(client)
        store = await seed_store()

        # Approve KYC
        resp_app = await client.post(f"/admin/merchants/{store.merchant_id}/kyc/approve")
        assert resp_app.status_code == 303
        async with async_session_factory() as db:
            m = await db.get(Merchant, store.merchant_id)
            assert m.kyc_status == KycStatus.APPROVED

        # Reject KYC
        resp_rej = await client.post(
            f"/admin/merchants/{store.merchant_id}/kyc/reject",
            data={"rejection_reason": "Invalid GST certificate"},
        )
        assert resp_rej.status_code == 303
        async with async_session_factory() as db:
            m = await db.get(Merchant, store.merchant_id)
            assert m.kyc_status == KycStatus.REJECTED
            assert m.kyc_rejection_reason == "Invalid GST certificate"

    async def test_admin_merchant_detail_view_html(self, client: AsyncClient):
        await self._login_admin(client)
        store = await seed_store()
        resp = await client.get(f"/admin/merchants/{store.merchant_id}")
        assert resp.status_code == 200
        html = resp.text
        assert "Subscription &amp; Trial Management" in html or "Subscription & Trial Management" in html
        assert "Extend Trial / Subscription Duration" in html
        assert "+90 Days" in html
        assert "Set Exact Expiration Date:" in html
