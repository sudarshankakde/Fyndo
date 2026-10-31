"""Tier 5 Adversarial Coverage Hardening Test Suite.

Stress-tests white-box edge cases:
1. Dynamic Expiration Transitions (sub-second boundaries, exact equality, leap years, non-UTC offsets).
2. Admin Extension Edge Cases (sequential cumulative extensions, zero durations, negative rejections, non-admin callers).
3. Content Gating Edge Cases (cashiers with/without permissions, offer validity extensions, draft to trial transitions).
"""
import uuid
from datetime import datetime, timedelta, timezone
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.database import async_session_factory
from app.main import app
from app.models.merchant import Merchant, MerchantStaff, SubscriptionStatus, as_aware
from tests.e2e_subscriptions.helpers import (
    assert_error_envelope,
    bearer,
    prepare_schema,
    reel_payload,
    seed_admin,
    seed_store,
    seed_user,
    set_auto_approve,
    set_auto_approve_kyc,
    set_subscription_in_db,
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


class TestTier5TemporalAndBoundaryAdversarial:
    """Stress tests dynamic expiration evaluation under extreme temporal conditions."""

    async def test_subsecond_precision_and_exact_equality(self):
        m = Merchant(
            user_id=uuid.uuid4(), business_name="Subsecond Store",
            subscription_status=SubscriptionStatus.ACTIVE
        )
        now = datetime.now(timezone.utc)

        # 500 microseconds in future -> ACTIVE
        m.subscription_expires_at = now + timedelta(microseconds=500)
        assert m.is_subscription_active is True
        assert m.effective_subscription_status == "ACTIVE"

        # 500 microseconds in past -> EXPIRED
        m.subscription_expires_at = now - timedelta(microseconds=500)
        assert m.is_subscription_active is False
        assert m.effective_subscription_status == "EXPIRED"

        # Exact equality now -> EXPIRED
        m.subscription_expires_at = now
        assert m.is_subscription_active is False
        assert m.effective_subscription_status == "EXPIRED"

    async def test_leap_year_rollover_and_duration_math(self):
        m = Merchant(
            user_id=uuid.uuid4(), business_name="Leap Year Store",
            subscription_status=SubscriptionStatus.ACTIVE
        )
        leap_start = datetime(2028, 2, 29, 12, 0, 0, tzinfo=timezone.utc)
        m.subscription_start_date = leap_start
        m.subscription_expires_at = leap_start + timedelta(days=90)
        # 2028 is a leap year (Feb 29 exists) -> +90 days lands on May 29, 2028
        assert m.subscription_expires_at == datetime(2028, 5, 29, 12, 0, 0, tzinfo=timezone.utc)

        # as_aware handles ISO string with leap year and microseconds
        iso_str = "2028-02-29T23:59:59.999999Z"
        aware_dt = as_aware(iso_str)
        assert aware_dt is not None
        assert aware_dt.year == 2028 and aware_dt.month == 2 and aware_dt.day == 29
        assert aware_dt.microsecond == 999999
        assert aware_dt.tzinfo == timezone.utc

    async def test_timezone_boundary_offsets(self):
        m = Merchant(
            user_id=uuid.uuid4(), business_name="Timezone Store",
            subscription_status=SubscriptionStatus.ACTIVE
        )
        now = datetime.now(timezone.utc)
        ist = timezone(timedelta(hours=5, minutes=30))
        pst = timezone(timedelta(hours=-8))

        # +2 hours in IST -> ACTIVE
        m.subscription_expires_at = (now + timedelta(hours=2)).astimezone(ist)
        assert m.is_subscription_active is True
        assert m.effective_subscription_status == "ACTIVE"

        # -2 hours in PST -> EXPIRED
        m.subscription_expires_at = (now - timedelta(hours=2)).astimezone(pst)
        assert m.is_subscription_active is False
        assert m.effective_subscription_status == "EXPIRED"


class TestTier5AdminAdversarial:
    """Stress tests admin endpoints under sequential, invalid, and unauthorized inputs."""

    async def test_admin_sequential_cumulative_extensions(self, client: AsyncClient):
        store = await seed_store()
        _, admin_token = await seed_admin()
        now = utcnow()
        past = now - timedelta(days=10)
        await set_subscription_in_db(store.merchant_id, status="EXPIRED", expires_at=past)

        url = f"/api/v1/admin/merchants/{store.merchant_id}/subscription/extend"
        headers = bearer(admin_token)

        # 1. First extension: 30 days from now (since expired in past)
        r1 = await client.post(url, json={"duration_days": 30}, headers=headers)
        assert r1.status_code == 200
        d1 = r1.json()["data"]
        exp1 = datetime.fromisoformat(d1["subscription_expires_at"].replace("Z", "+00:00"))
        assert 29 <= (exp1 - now).total_seconds() / 86400 <= 31

        # 2. Second extension: 45 days (must add to current future expiry exp1)
        r2 = await client.post(url, json={"duration_days": 45}, headers=headers)
        assert r2.status_code == 200
        d2 = r2.json()["data"]
        exp2 = datetime.fromisoformat(d2["subscription_expires_at"].replace("Z", "+00:00"))
        assert 44 <= (exp2 - exp1).total_seconds() / 86400 <= 46

        # 3. Third extension: months=2 (60 days, must add to exp2)
        r3 = await client.post(url, json={"months": 2}, headers=headers)
        assert r3.status_code == 200
        d3 = r3.json()["data"]
        exp3 = datetime.fromisoformat(d3["subscription_expires_at"].replace("Z", "+00:00"))
        assert 59 <= (exp3 - exp2).total_seconds() / 86400 <= 61
        assert d3["is_subscription_active"] is True
        assert d3["subscription_status"] == "ACTIVE"

    async def test_admin_extend_negative_and_zero_edge_cases(self, client: AsyncClient):
        store = await seed_store()
        _, admin_token = await seed_admin()
        url = f"/api/v1/admin/merchants/{store.merchant_id}/subscription/extend"
        headers = bearer(admin_token)

        # Negative duration rejected with 422
        r_neg1 = await client.post(url, json={"duration_days": -10}, headers=headers)
        assert r_neg1.status_code == 422
        r_neg2 = await client.post(url, json={"months": -1}, headers=headers)
        assert r_neg2.status_code == 422

        # 0 days, 0 months -> allowed, adds 0 days
        r_zero = await client.post(url, json={"duration_days": 0, "months": 0}, headers=headers)
        assert r_zero.status_code == 200
        assert r_zero.json().get("success") is True

    async def test_admin_update_empty_and_null_rejection(self, client: AsyncClient):
        store = await seed_store()
        _, admin_token = await seed_admin()
        url = f"/api/v1/admin/merchants/{store.merchant_id}/subscription"
        headers = bearer(admin_token)

        # Empty body -> 422
        r1 = await client.put(url, json={}, headers=headers)
        assert r1.status_code == 422

        # Both fields null -> 422
        r2 = await client.put(url, json={"subscription_status": None, "subscription_expires_at": None}, headers=headers)
        assert r2.status_code == 422

    async def test_admin_endpoints_non_admin_forbidden(self, client: AsyncClient):
        store = await seed_store(with_staff=True)
        _, shopper_token = await seed_user("SHOPPER")
        cashier_token = store.staff_token

        endpoints = [
            ("GET", f"/api/v1/admin/merchants/{store.merchant_id}"),
            ("PUT", f"/api/v1/admin/merchants/{store.merchant_id}/subscription"),
            ("POST", f"/api/v1/admin/merchants/{store.merchant_id}/subscription/extend"),
        ]
        for method, ep in endpoints:
            # Anonymous -> 401
            r_anon = await client.request(method, ep, json={"duration_days": 30})
            assert r_anon.status_code == 401

            # Shopper -> 403
            r_shopper = await client.request(method, ep, json={"duration_days": 30}, headers=bearer(shopper_token))
            assert r_shopper.status_code == 403

            # Cashier -> 403
            r_cashier = await client.request(method, ep, json={"duration_days": 30}, headers=bearer(cashier_token))
            assert r_cashier.status_code == 403


class TestTier5GatingAdversarial:
    """Stress tests content gating on offer validity extension and cashier roles."""

    async def test_extend_offer_validity_blocked_for_expired_merchant(self, client: AsyncClient):
        store = await seed_store()
        # Create live reel
        r = await client.post("/api/v1/reels", json=reel_payload(validity_days=2), headers=bearer(store.owner_token))
        assert r.status_code in (200, 201)
        reel_id = r.json()["data"]["reel_id"]

        # Expire merchant subscription
        past = utcnow() - timedelta(hours=2)
        await set_subscription_in_db(store.merchant_id, status="EXPIRED", expires_at=past)

        # Attempt offer extension -> 403
        r_ext = await client.post(
            f"/api/v1/reels/{reel_id}/extend-validity",
            json={"additional_days": 3},
            headers=bearer(store.owner_token),
        )
        assert r_ext.status_code == 403
        assert_error_envelope(r_ext.json(), expected_status_code=403, expected_code="HTTP_403")

    async def test_cashier_content_management_gated_by_store_subscription(self, client: AsyncClient):
        # Seed store with staff having can_upload_reels=True
        store = await seed_store(with_staff=True, can_upload_reels=True)
        # Enable can_manage_content directly on staff
        async with async_session_factory() as db:
            staff_res = await db.execute(select(MerchantStaff).where(MerchantStaff.id == store.staff_id))
            staff = staff_res.scalars().first()
            if staff:
                staff.can_manage_content = True
                await db.commit()

        # Create live reel by owner
        r = await client.post("/api/v1/reels", json=reel_payload(validity_days=2), headers=bearer(store.owner_token))
        assert r.status_code in (200, 201)
        reel_id = r.json()["data"]["reel_id"]

        # 1. Active store -> cashier with can_manage_content succeeds
        r_ok = await client.post(
            f"/api/v1/reels/{reel_id}/extend-validity",
            json={"additional_days": 3},
            headers=bearer(store.staff_token),
        )
        assert r_ok.status_code == 200

        # 2. Expire store subscription -> cashier with can_manage_content is blocked with 403
        await set_subscription_in_db(store.merchant_id, status="EXPIRED", expires_at=utcnow() - timedelta(days=1))
        r_blocked = await client.post(
            f"/api/v1/reels/{reel_id}/extend-validity",
            json={"additional_days": 3},
            headers=bearer(store.staff_token),
        )
        assert r_blocked.status_code == 403
        assert_error_envelope(r_blocked.json(), expected_status_code=403, expected_code="HTTP_403")

    async def test_onboarding_draft_to_trial_activation_lifecycle(self, client: AsyncClient):
        _, token = await seed_user("MERCHANT")
        # Draft step
        draft = {"business_name": "Lifecycle Store", "sector": "FOOD", "step": 1}
        d_res = await client.put("/api/v1/merchants/onboard/draft", json=draft, headers=bearer(token))
        assert d_res.status_code == 200

        # Profile is not active yet
        p_res = await client.get("/api/v1/merchants/profile", headers=bearer(token))
        assert p_res.status_code in (401, 403, 404)

        # Complete onboarding
        onboard_payload = {
            "business_name": "Lifecycle Store",
            "sector": "FOOD",
            "address_text": "Sitabuldi Square",
            "city": "Nagpur",
            "latitude": 21.1458,
            "longitude": 79.0882,
            "kyc_doc_url": "https://res.cloudinary.com/fyndo/kyc.pdf",
        }
        ob_res = await client.post("/api/v1/merchants/onboard", json=onboard_payload, headers=bearer(token))
        assert ob_res.status_code == 200
        ob_data = ob_res.json()["data"]
        assert ob_data["subscription_status"] == "ACTIVE"
        assert ob_data["is_subscription_active"] is True
        exp = datetime.fromisoformat(ob_data["subscription_expires_at"].replace("Z", "+00:00"))
        assert 89 <= (exp - utcnow()).total_seconds() / 86400 <= 92
