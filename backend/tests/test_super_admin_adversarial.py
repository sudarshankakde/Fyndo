"""Adversarial and stress test harness for the Super Admin Panel.
Written by Challenger to stress-test route precedence, authentication boundaries,
bulk operation corner cases, and malformed inputs.
"""
import uuid
from datetime import datetime, timedelta, timezone
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from app.core.config import settings
from app.core.database import async_session_factory
from app.core.security import create_access_token
from app.main import app
from app.models import KycStatus, Merchant, Reel, ReelStatus, SubscriptionStatus, User
from app.models.audit_log import AuditLog
from app.models.system_settings import SystemSetting
from tests.e2e_subscriptions.helpers import prepare_schema, seed_store, seed_user

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture(autouse=True)
async def init_clean_db():
    await prepare_schema()
    async with async_session_factory() as db:
        await db.execute(delete(SystemSetting))
        await db.execute(delete(AuditLog))
        await db.commit()
    yield


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _login_as_super_admin(client: AsyncClient) -> None:
    res = await client.post(
        "/admin/login",
        data={"identifier": settings.SUPER_ADMIN_IDENTIFIER, "password": settings.SUPER_ADMIN_PASSWORD},
    )
    assert res.status_code == 303
    assert "fyndo_admin_session" in client.cookies


# ==============================================================================
# SECTION 1: Route Precedence Adversarial Verification
# ==============================================================================
class TestRoutePrecedence:
    """Verifies that none of the 10 custom pages are shadowed by /{model_key} catch-alls."""

    async def test_merchants_list_precedence_over_generic(self, client: AsyncClient):
        await _login_as_super_admin(client)
        resp = await client.get("/admin/merchants")
        assert resp.status_code == 200
        # Dedicated merchant template markers
        assert "Merchant Directory & Accounts" in resp.text
        assert "Extend All Expired (+90d)" in resp.text
        assert "Approve All Pending KYC" in resp.text
        # Generic list template uses generic "Records" or "Add Merchant"
        assert "Records" not in resp.text

    async def test_merchants_detail_precedence_over_generic(self, client: AsyncClient):
        await _login_as_super_admin(client)
        store = await seed_store()
        resp = await client.get(f"/admin/merchants/{store.merchant_id}")
        assert resp.status_code == 200
        # Custom merchant detail view markers
        assert "Store Profile & KYC" in resp.text
        assert "Subscription &" in resp.text
        assert "Store Staff & Cashier Terminals" in resp.text
        assert "Reel Promotion History" in resp.text

    async def test_subscriptions_precedence_over_generic(self, client: AsyncClient):
        await _login_as_super_admin(client)
        resp = await client.get("/admin/subscriptions")
        assert resp.status_code == 200
        assert "Subscription Management" in resp.text
        assert "Active Subscriptions" in resp.text
        assert "Expiring Soon" in resp.text

    async def test_subscriptions_csv_export_route_not_swallowed(self, client: AsyncClient):
        await _login_as_super_admin(client)
        resp = await client.get("/admin/subscriptions/export-csv")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/csv")
        assert "Merchant ID" in resp.text
        assert "Business Name" in resp.text

    async def test_kyc_queue_precedence_over_generic(self, client: AsyncClient):
        await _login_as_super_admin(client)
        resp = await client.get("/admin/kyc")
        assert resp.status_code == 200
        assert "Store KYC Verification Queue" in resp.text
        assert "Pending Verification" in resp.text
        assert "Approved Stores" in resp.text

    async def test_users_management_precedence_over_generic(self, client: AsyncClient):
        await _login_as_super_admin(client)
        resp = await client.get("/admin/users")
        assert resp.status_code == 200
        assert "User Management &" in resp.text
        assert "Role Filters" in resp.text or "SHOPPER" in resp.text

    async def test_users_htmx_partial_precedence(self, client: AsyncClient):
        await _login_as_super_admin(client)
        resp = await client.get("/admin/users", headers={"HX-Request": "true"})
        assert resp.status_code == 200
        assert "<html" not in resp.text.lower()
        assert "card-head" in resp.text

    async def test_settings_precedence_over_generic(self, client: AsyncClient):
        await _login_as_super_admin(client)
        resp = await client.get("/admin/settings")
        assert resp.status_code == 200
        assert "Platform Settings" in resp.text
        assert "Merchant Auto-Trial" in resp.text
        assert "Auto-Reel Moderation" in resp.text
        assert "Maintenance Mode" in resp.text

    async def test_audit_log_precedence_over_generic(self, client: AsyncClient):
        await _login_as_super_admin(client)
        resp = await client.get("/admin/audit")
        assert resp.status_code == 200
        assert "Operational Audit Log" in resp.text

    async def test_analytics_precedence_over_generic(self, client: AsyncClient):
        await _login_as_super_admin(client)
        resp = await client.get("/admin/analytics")
        assert resp.status_code == 200
        assert "Platform Performance Analytics" in resp.text
        assert "Merchant Signups Timeline" in resp.text

    async def test_moderation_precedence_over_generic(self, client: AsyncClient):
        await _login_as_super_admin(client)
        resp = await client.get("/admin/moderation")
        assert resp.status_code == 200
        assert "Reel Moderation" in resp.text

    async def test_generic_crud_remains_functional_for_unoverridden_models(self, client: AsyncClient):
        """Ensures adding dedicated view routers did not destroy generic CRUD for remaining models."""
        await _login_as_super_admin(client)
        resp = await client.get("/admin/merchant_staff")
        assert resp.status_code == 200
        assert "Merchant Staff" in resp.text


# ==============================================================================
# SECTION 2: Security & Session Verification (Adversarial)
# ==============================================================================
class TestSecurityBoundaries:
    """Verifies that all admin endpoints bounce unauthenticated / unauthorized requests to /admin/login."""

    UNAUTH_ENDPOINTS = [
        ("GET", "/admin/"),
        ("GET", "/admin/merchants"),
        ("GET", f"/admin/merchants/{uuid.uuid4()}"),
        ("POST", f"/admin/merchants/{uuid.uuid4()}/subscription/activate"),
        ("POST", f"/admin/merchants/{uuid.uuid4()}/subscription/extend"),
        ("POST", f"/admin/merchants/{uuid.uuid4()}/subscription/set-expiry"),
        ("POST", f"/admin/merchants/{uuid.uuid4()}/subscription/deactivate"),
        ("POST", f"/admin/merchants/{uuid.uuid4()}/kyc/approve"),
        ("POST", f"/admin/merchants/{uuid.uuid4()}/kyc/reject"),
        ("POST", "/admin/merchants/bulk/extend-expired"),
        ("POST", "/admin/merchants/bulk/approve-kyc"),
        ("GET", "/admin/subscriptions"),
        ("POST", "/admin/subscriptions/bulk-extend"),
        ("GET", "/admin/subscriptions/export-csv"),
        ("GET", "/admin/kyc"),
        ("POST", f"/admin/kyc/{uuid.uuid4()}/approve"),
        ("POST", f"/admin/kyc/{uuid.uuid4()}/reject"),
        ("POST", "/admin/kyc/bulk-approve"),
        ("GET", "/admin/users"),
        ("POST", f"/admin/users/{uuid.uuid4()}/ban"),
        ("POST", f"/admin/users/{uuid.uuid4()}/unban"),
        ("GET", "/admin/moderation"),
        ("POST", f"/admin/moderation/reels/{uuid.uuid4()}/approve"),
        ("POST", f"/admin/moderation/reels/{uuid.uuid4()}/reject"),
        ("GET", "/admin/settings"),
        ("POST", "/admin/settings/auto-trial"),
        ("POST", "/admin/settings/auto-approve"),
        ("POST", "/admin/settings/auto-approve-kyc"),
        ("POST", "/admin/settings/maintenance-mode"),
        ("GET", "/admin/audit"),
        ("GET", "/admin/audit-logs"),
        ("GET", "/admin/analytics"),
        ("POST", "/admin/system/cache/flush"),
    ]

    @pytest.mark.parametrize("method,path", UNAUTH_ENDPOINTS)
    async def test_unauthenticated_request_bounces_to_login(self, client: AsyncClient, method: str, path: str):
        if method == "GET":
            resp = await client.get(path, follow_redirects=False)
        else:
            resp = await client.post(path, data={}, follow_redirects=False)
        assert resp.status_code == 303, f"{method} {path} returned status {resp.status_code}"
        assert resp.headers["location"] == "/admin/login", f"{method} {path} redirected to {resp.headers.get('location')}"

    async def test_tampered_cookie_bounces_to_login(self, client: AsyncClient):
        client.cookies.set("fyndo_admin_session", "forged_malicious_token")
        resp = await client.get("/admin/merchants", follow_redirects=False)
        assert resp.status_code == 303
        assert resp.headers["location"] == "/admin/login"

    async def test_shopper_jwt_cannot_access_admin_panel(self, client: AsyncClient):
        # A token with role="SHOPPER" and standard API scope
        shopper_token = create_access_token(subject=str(uuid.uuid4()), role="SHOPPER")
        client.cookies.set("fyndo_admin_session", shopper_token)
        resp = await client.get("/admin/merchants", follow_redirects=False)
        assert resp.status_code == 303
        assert resp.headers["location"] == "/admin/login"


# ==============================================================================
# SECTION 3: Robustness of Actions & Stress Tests
# ==============================================================================
class TestActionRobustnessAndStress:
    """Stress tests bulk actions, edge cases, malformed payloads, and state isolation."""

    async def test_bulk_extend_on_empty_merchants(self, client: AsyncClient):
        await _login_as_super_admin(client)
        # Ensure zero expired merchants exist in database
        async with async_session_factory() as db:
            merchants = (await db.execute(select(Merchant))).scalars().all()
            for m in merchants:
                m.subscription_status = SubscriptionStatus.ACTIVE
                m.subscription_expires_at = datetime.now(timezone.utc) + timedelta(days=30)
            await db.commit()

        resp = await client.post("/admin/merchants/bulk/extend-expired", follow_redirects=False)
        assert resp.status_code == 303
        assert "ok=" in resp.headers["location"]
        assert "0+expired" in resp.headers["location"]

        resp2 = await client.post("/admin/subscriptions/bulk-extend", data={"duration_days": "60"}, follow_redirects=False)
        assert resp2.status_code == 303
        assert "ok=" in resp2.headers["location"]
        assert "0+expired" in resp2.headers["location"]

    async def test_bulk_kyc_approve_on_empty_merchants(self, client: AsyncClient):
        await _login_as_super_admin(client)
        # Ensure zero pending KYC merchants exist in database
        async with async_session_factory() as db:
            merchants = (await db.execute(select(Merchant))).scalars().all()
            for m in merchants:
                m.kyc_status = KycStatus.APPROVED
            await db.commit()

        resp = await client.post("/admin/merchants/bulk/approve-kyc", follow_redirects=False)
        assert resp.status_code == 303
        assert "ok=" in resp.headers["location"]
        assert "0+pending" in resp.headers["location"]

        resp2 = await client.post("/admin/kyc/bulk-approve", follow_redirects=False)
        assert resp2.status_code == 303
        assert "ok=" in resp2.headers["location"]
        assert "0+pending" in resp2.headers["location"]

    async def test_bulk_kyc_approve_preserves_rejected_and_approved_states(self, client: AsyncClient):
        """CRITICAL: Bulk KYC approve must ONLY approve PENDING merchants, never touch REJECTED."""
        await _login_as_super_admin(client)
        s1 = await seed_store()
        s2 = await seed_store()
        s3 = await seed_store()

        async with async_session_factory() as db:
            m1 = await db.get(Merchant, s1.merchant_id)
            m1.kyc_status = KycStatus.APPROVED

            m2 = await db.get(Merchant, s2.merchant_id)
            m2.kyc_status = KycStatus.PENDING

            m3 = await db.get(Merchant, s3.merchant_id)
            m3.kyc_status = KycStatus.REJECTED
            m3.kyc_rejection_reason = "Permanent fraud rejection"
            await db.commit()

        resp = await client.post("/admin/kyc/bulk-approve")
        assert resp.status_code == 303

        async with async_session_factory() as db:
            m1_after = await db.get(Merchant, s1.merchant_id)
            m2_after = await db.get(Merchant, s2.merchant_id)
            m3_after = await db.get(Merchant, s3.merchant_id)

            assert m1_after.kyc_status == KycStatus.APPROVED
            assert m2_after.kyc_status == KycStatus.APPROVED  # Converted
            assert m3_after.kyc_status == KycStatus.REJECTED  # Unchanged!
            assert m3_after.kyc_rejection_reason == "Permanent fraud rejection"

    async def test_bulk_subscription_extend_preserves_unexpired_active_merchants(self, client: AsyncClient):
        """Bulk extend should only extend expired subscriptions, not overwrite unexpired ones."""
        await _login_as_super_admin(client)
        s1 = await seed_store()
        s2 = await seed_store()

        future_date = datetime.now(timezone.utc) + timedelta(days=60)
        past_date = datetime.now(timezone.utc) - timedelta(days=10)

        async with async_session_factory() as db:
            m1 = await db.get(Merchant, s1.merchant_id)
            m1.subscription_status = SubscriptionStatus.ACTIVE
            m1.subscription_expires_at = future_date

            m2 = await db.get(Merchant, s2.merchant_id)
            m2.subscription_status = SubscriptionStatus.EXPIRED
            m2.subscription_expires_at = past_date
            await db.commit()

        resp = await client.post("/admin/subscriptions/bulk-extend", data={"duration_days": "45"})
        assert resp.status_code == 303

        async with async_session_factory() as db:
            m1_after = await db.get(Merchant, s1.merchant_id)
            m2_after = await db.get(Merchant, s2.merchant_id)

            # m1 expiry was unchanged (+60 days)
            assert abs((m1_after.subscription_expires_at - future_date).total_seconds()) < 5
            # m2 was expired, now ACTIVE with ~ +45 days
            assert m2_after.subscription_status == SubscriptionStatus.ACTIVE
            assert m2_after.subscription_expires_at > datetime.now(timezone.utc) + timedelta(days=40)

    async def test_bulk_extend_with_malformed_duration_days(self, client: AsyncClient):
        await _login_as_super_admin(client)
        s = await seed_store()
        async with async_session_factory() as db:
            m = await db.get(Merchant, s.merchant_id)
            m.subscription_status = SubscriptionStatus.EXPIRED
            m.subscription_expires_at = datetime.now(timezone.utc) - timedelta(days=1)
            await db.commit()

        # Malformed text
        resp = await client.post("/admin/subscriptions/bulk-extend", data={"duration_days": "non_a_number"})
        assert resp.status_code == 303

        # Negative number (should clamp or default safely)
        resp2 = await client.post("/admin/subscriptions/bulk-extend", data={"duration_days": "-500"})
        assert resp2.status_code == 303

    async def test_invalid_uuid_inputs_return_proper_error_codes(self, client: AsyncClient):
        await _login_as_super_admin(client)
        # Invalid UUID format should yield 400
        r1 = await client.get("/admin/merchants/not-a-valid-uuid")
        assert r1.status_code == 400

        # Non-existent UUID should yield 404
        non_existent = str(uuid.uuid4())
        r2 = await client.get(f"/admin/merchants/{non_existent}")
        assert r2.status_code == 404

        r3 = await client.post(f"/admin/users/not-a-valid-uuid/ban")
        assert r3.status_code == 400

        r4 = await client.post(f"/admin/users/{non_existent}/ban")
        assert r4.status_code == 404

        r5 = await client.post(f"/admin/kyc/not-a-valid-uuid/approve")
        assert r5.status_code == 400

        r6 = await client.post(f"/admin/kyc/{non_existent}/approve")
        assert r6.status_code == 404

    async def test_merchant_set_expiry_invalid_date_formats(self, client: AsyncClient):
        await _login_as_super_admin(client)
        store = await seed_store()

        # Completely invalid format
        r1 = await client.post(
            f"/admin/merchants/{store.merchant_id}/subscription/set-expiry",
            data={"expiry_date": "yesterday"},
            follow_redirects=False,
        )
        assert r1.status_code == 303
        assert "err=" in r1.headers["location"]

        # Empty date
        r2 = await client.post(
            f"/admin/merchants/{store.merchant_id}/subscription/set-expiry",
            data={"expiry_date": ""},
            follow_redirects=False,
        )
        assert r2.status_code == 303
        assert "err=" in r2.headers["location"]

    async def test_kyc_reject_with_empty_reason_uses_fallback(self, client: AsyncClient):
        await _login_as_super_admin(client)
        store = await seed_store()

        resp = await client.post(
            f"/admin/kyc/{store.merchant_id}/reject",
            data={"rejection_reason": ""},
        )
        assert resp.status_code == 303

        async with async_session_factory() as db:
            m = await db.get(Merchant, store.merchant_id)
            assert m.kyc_status == KycStatus.REJECTED
            assert len(m.kyc_rejection_reason) > 0  # Fallback reason populated
