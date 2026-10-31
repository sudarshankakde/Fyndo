"""Comprehensive test suite for the 10 Super Admin panel pages and workflows."""
import uuid
from datetime import timedelta
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from app.core.config import settings
from app.core.database import async_session_factory
from app.main import app
from app.models import KycStatus, Merchant, Reel, ReelStatus, SubscriptionStatus, User
from app.models.audit_log import AuditLog
from app.models.system_settings import MAINTENANCE_MODE, SystemSetting
from tests.e2e_subscriptions.helpers import prepare_schema, seed_store, seed_user, set_subscription_in_db, utcnow

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture(autouse=True)
async def init_db():
    await prepare_schema()
    async with async_session_factory() as db:
        await db.execute(delete(SystemSetting))
        await db.commit()
    yield


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _login(client: AsyncClient) -> None:
    res = await client.post(
        "/admin/login",
        data={"identifier": settings.SUPER_ADMIN_IDENTIFIER, "password": settings.SUPER_ADMIN_PASSWORD},
    )
    assert res.status_code == 303


class TestSuperAdminPages:
    """Verifies all 10 Super Admin panel endpoints, views, and actions."""

    # 1. Enhanced Dashboard
    async def test_01_enhanced_dashboard(self, client: AsyncClient):
        await _login(client)
        store = await seed_store()
        resp = await client.get("/admin/")
        assert resp.status_code == 200
        html = resp.text
        assert "Active Subscriptions" in html
        assert "Expired Subscriptions" in html
        assert "Awaiting KYC review" in html
        assert "Reels pending moderation" in html
        assert "Quick Operations:" in html
        assert "/admin/kyc" in html
        assert "/admin/subscriptions" in html

    # 2. Merchant List & Bulk Actions
    async def test_02_merchant_list_and_bulk_actions(self, client: AsyncClient):
        await _login(client)
        store = await seed_store()
        resp = await client.get("/admin/merchants?sub_filter=ACTIVE&kyc_filter=ALL")
        assert resp.status_code == 200
        assert "Feature Test Store" in resp.text or str(store.merchant_id) in resp.text

        # Bulk extend expired
        bulk_ext = await client.post("/admin/merchants/bulk/extend-expired")
        assert bulk_ext.status_code == 303

        # Bulk approve KYC
        bulk_kyc = await client.post("/admin/merchants/bulk/approve-kyc")
        assert bulk_kyc.status_code == 303

    # 3. Merchant Detail & Controls
    async def test_03_merchant_detail_and_controls(self, client: AsyncClient):
        await _login(client)
        store = await seed_store()
        resp = await client.get(f"/admin/merchants/{store.merchant_id}")
        assert resp.status_code == 200
        assert "Store Profile & KYC" in resp.text
        assert "Subscription &amp; Trial Management" in resp.text or "Subscription & Trial Management" in resp.text

        # Subscription controls
        act = await client.post(f"/admin/merchants/{store.merchant_id}/subscription/activate", data={"duration_days": "45"})
        assert act.status_code == 303
        ext = await client.post(f"/admin/merchants/{store.merchant_id}/subscription/extend", data={"duration_days": "30"})
        assert ext.status_code == 303
        exp = await client.post(f"/admin/merchants/{store.merchant_id}/subscription/set-expiry", data={"expiry_date": "2028-06-30"})
        assert exp.status_code == 303
        deact = await client.post(f"/admin/merchants/{store.merchant_id}/subscription/deactivate")
        assert deact.status_code == 303

        # KYC controls
        appr = await client.post(f"/admin/merchants/{store.merchant_id}/kyc/approve")
        assert appr.status_code == 303
        rej = await client.post(f"/admin/merchants/{store.merchant_id}/kyc/reject", data={"rejection_reason": "Invalid docs"})
        assert rej.status_code == 303

    # 4. Subscription Management & CSV Export
    async def test_04_subscription_management_and_csv(self, client: AsyncClient):
        await _login(client)
        store = await seed_store()
        resp = await client.get("/admin/subscriptions?filter=ALL")
        assert resp.status_code == 200
        assert "Subscription Management" in resp.text
        assert "Active Subscriptions" in resp.text

        bulk = await client.post("/admin/subscriptions/bulk-extend", data={"duration_days": "60"})
        assert bulk.status_code == 303

        csv_resp = await client.get("/admin/subscriptions/export-csv")
        assert csv_resp.status_code == 200
        assert "text/csv" in csv_resp.headers["content-type"]
        assert "Business Name" in csv_resp.text
        assert "Feature Test Store" in csv_resp.text or str(store.merchant_id) in csv_resp.text

    # 5. KYC Queue
    async def test_05_kyc_queue_and_actions(self, client: AsyncClient):
        await _login(client)
        store = await seed_store()
        async with async_session_factory() as db:
            m = await db.get(Merchant, store.merchant_id)
            m.kyc_status = KycStatus.PENDING
            await db.commit()

        resp = await client.get("/admin/kyc?status=PENDING")
        assert resp.status_code == 200
        assert "Store KYC Verification Queue" in resp.text

        appr = await client.post(f"/admin/kyc/{store.merchant_id}/approve")
        assert appr.status_code == 303

        rej = await client.post(f"/admin/kyc/{store.merchant_id}/reject", data={"rejection_reason": "Blurry document"})
        assert rej.status_code == 303

        bulk = await client.post("/admin/kyc/bulk-approve")
        assert bulk.status_code == 303

    # 6. User Management & Ban/Unban
    async def test_06_user_management_and_ban(self, client: AsyncClient):
        await _login(client)
        user_id, _ = await seed_user("SHOPPER", "Admin Test Shopper")

        resp = await client.get("/admin/users?role=SHOPPER")
        assert resp.status_code == 200
        assert "User Management &amp; Access Control" in resp.text or "User Management & Access Control" in resp.text

        # Ban
        ban = await client.post(f"/admin/users/{user_id}/ban")
        assert ban.status_code == 303
        async with async_session_factory() as db:
            u = await db.get(User, user_id)
            assert u.is_active is False

        # Unban
        unban = await client.post(f"/admin/users/{user_id}/unban")
        assert unban.status_code == 303
        async with async_session_factory() as db:
            u = await db.get(User, user_id)
            assert u.is_active is True

    # 7. Reel Moderation
    async def test_07_reel_moderation(self, client: AsyncClient):
        await _login(client)
        store = await seed_store()
        async with async_session_factory() as db:
            reel = Reel(
                merchant_id=store.merchant_id,
                title="Grand Opening Offer",
                video_url="https://example.com/video.mp4",
                thumbnail_url="https://example.com/thumb.jpg",
                duration_seconds=30,
                status=ReelStatus.PENDING_MODERATION,
            )
            db.add(reel)
            await db.commit()
            reel_id = reel.id

        resp = await client.get("/admin/moderation?status=PENDING_MODERATION")
        assert resp.status_code == 200
        assert "Reel Moderation" in resp.text

        appr = await client.post(f"/admin/moderation/reels/{reel_id}/approve")
        assert appr.status_code == 303
        async with async_session_factory() as db:
            r = await db.get(Reel, reel_id)
            assert r.status == ReelStatus.APPROVED

        rej = await client.post(f"/admin/moderation/reels/{reel_id}/reject", data={"rejection_reason": "Low resolution"})
        assert rej.status_code == 303
        async with async_session_factory() as db:
            r = await db.get(Reel, reel_id)
            assert r.status == ReelStatus.REJECTED

    # 8. Platform Settings
    async def test_08_platform_settings(self, client: AsyncClient):
        await _login(client)
        resp = await client.get("/admin/settings")
        assert resp.status_code == 200
        assert "Platform Settings" in resp.text

        # Toggles
        trial = await client.post("/admin/settings/auto-trial", data={"enabled": "on", "duration_days": "100"})
        assert trial.status_code == 303
        reels = await client.post("/admin/settings/auto-approve", data={"enabled": "on"})
        assert reels.status_code == 303
        kyc = await client.post("/admin/settings/auto-approve-kyc", data={"enabled": "on"})
        assert kyc.status_code == 303
        maint = await client.post("/admin/settings/maintenance-mode", data={"enabled": "on"})
        assert maint.status_code == 303

    # 9. Audit Log & Audit-Logs Alias
    async def test_09_audit_log_and_alias(self, client: AsyncClient):
        await _login(client)
        async with async_session_factory() as db:
            log = AuditLog(
                admin_user="+919999900000",
                action="test.action",
                target_type="merchant",
                target_id="test-target",
                details={"key": "val"},
                outcome="success",
            )
            db.add(log)
            await db.commit()

        # Test both /admin/audit and /admin/audit-logs alias
        resp1 = await client.get("/admin/audit")
        assert resp1.status_code == 200
        assert "Operational Audit Log" in resp1.text
        assert "test.action" in resp1.text

        resp2 = await client.get("/admin/audit-logs")
        assert resp2.status_code == 200
        assert "Operational Audit Log" in resp2.text

    # 10. Analytics Dashboard
    async def test_10_analytics_dashboard(self, client: AsyncClient):
        await _login(client)
        await seed_store()
        resp = await client.get("/admin/analytics")
        assert resp.status_code == 200
        assert "Platform Performance Analytics" in resp.text
        assert "Merchant Signups Timeline" in resp.text
        assert "signupsChart" in resp.text
