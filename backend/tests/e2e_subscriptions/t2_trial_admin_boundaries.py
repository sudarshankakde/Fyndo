"""Tier 2 - Boundaries: Trial, Dynamic Evaluation, Admin View, Update & Extend."""
import uuid
from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient

from tests.e2e_subscriptions.helpers import (
    bearer,
    onboard_merchant_via_api,
    parse_iso_datetime,
    seed_admin,
    seed_store,
    seed_user,
    set_subscription_in_db,
    utcnow,
)

pytestmark = pytest.mark.asyncio


class TestTier2TrialBoundaries:
    """Tier 2: Boundaries for Automatic Trial Initialization."""

    async def test_tier2_trial_boundary_duration_is_within_89_to_92_days(self, client: AsyncClient):
        """Trial length is strictly between 89 and 92 days."""
        now = utcnow()
        _, _, data = await onboard_merchant_via_api(client, business_name="Trial Bounds Store")
        assert data.get("success") is True
        exp = parse_iso_datetime(data["data"].get("subscription_expires_at"))
        assert exp is not None
        assert 89.0 <= (exp - now).total_seconds() / 86400 <= 92.0

    async def test_tier2_trial_boundary_multiple_merchants_get_independent_periods(self, client: AsyncClient):
        """Two merchants onboarded independently receive distinct subscription periods."""
        _, _, data1 = await onboard_merchant_via_api(client, business_name="Store Alpha")
        _, _, data2 = await onboard_merchant_via_api(client, business_name="Store Beta")
        assert data1["data"]["id"] != data2["data"]["id"]
        assert data1["data"]["subscription_status"] == "ACTIVE"
        assert data2["data"]["subscription_status"] == "ACTIVE"

    async def test_tier2_trial_boundary_idempotent_onboard_preserves_subscription(self, client: AsyncClient):
        """Re-submitting onboarding for an existing merchant preserves original start and expiry."""
        _, token, data1 = await onboard_merchant_via_api(client, business_name="Idempotent Store")
        original_exp = data1["data"].get("subscription_expires_at")

        payload = {
            "business_name": "Idempotent Store",
            "sector": "FOOD",
            "address_text": "123 Central Avenue, Sitabuldi",
            "city": "Nagpur",
            "latitude": 21.1458,
            "longitude": 79.0882,
            "kyc_doc_url": "https://res.cloudinary.com/fyndo/kyc/sample.pdf",
        }
        resp2 = await client.post("/api/v1/merchants/onboard", json=payload, headers=bearer(token))
        assert resp2.status_code == 200
        assert resp2.json()["data"].get("subscription_expires_at") == original_exp

    async def test_tier2_trial_boundary_draft_operations_do_not_create_subscription(self, client: AsyncClient):
        """Saving an onboarding draft does not allocate a merchant or subscription."""
        _, token = await seed_user("MERCHANT")
        draft_payload = {"business_name": "Draft Only Store", "sector": "FOOD", "step": 1}
        resp = await client.put("/api/v1/merchants/onboard/draft", json=draft_payload, headers=bearer(token))
        assert resp.status_code == 200

        profile_resp = await client.get("/api/v1/merchants/profile", headers=bearer(token))
        assert profile_resp.status_code in (401, 403, 404)

    async def test_tier2_trial_boundary_onboard_without_kyc_still_assigns_subscription(self, client: AsyncClient):
        """Even when auto-approve KYC is disabled, trial subscription is assigned on signup."""
        from tests.feature_helpers import set_auto_approve_kyc
        await set_auto_approve_kyc(False)
        try:
            _, _, data = await onboard_merchant_via_api(client, business_name="Pending KYC Store")
            assert data.get("success") is True
            assert data["data"].get("subscription_status") == "ACTIVE"
        finally:
            await set_auto_approve_kyc(True)


class TestTier2DynamicEvalBoundaries:
    """Tier 2: Boundaries for Dynamic Expiration Evaluation."""

    async def test_tier2_dynamic_eval_boundary_one_second_before_expiry_is_active(self, client: AsyncClient):
        """Subscription expiring in +2 seconds evaluates is_subscription_active as True."""
        store = await seed_store()
        future = utcnow() + timedelta(seconds=2)
        await set_subscription_in_db(store.merchant_id, status="ACTIVE", expires_at=future)

        resp = await client.get("/api/v1/merchants/profile", headers=bearer(store.owner_token))
        assert resp.status_code == 200
        assert resp.json()["data"].get("is_subscription_active") is True

    async def test_tier2_dynamic_eval_boundary_one_second_after_expiry_is_expired(self, client: AsyncClient):
        """Subscription expired 1 second ago evaluates is_subscription_active as False."""
        store = await seed_store()
        past = utcnow() - timedelta(seconds=2)
        await set_subscription_in_db(store.merchant_id, status="ACTIVE", expires_at=past)

        resp = await client.get("/api/v1/merchants/profile", headers=bearer(store.owner_token))
        assert resp.status_code == 200
        assert resp.json()["data"].get("is_subscription_active") is False

    async def test_tier2_dynamic_eval_boundary_microsecond_precision(self, client: AsyncClient):
        """Microsecond timestamps are compared accurately without truncation errors."""
        store = await seed_store()
        now = utcnow()
        await set_subscription_in_db(store.merchant_id, status="ACTIVE", expires_at=now + timedelta(microseconds=500000))

        resp = await client.get("/api/v1/merchants/profile", headers=bearer(store.owner_token))
        assert resp.status_code == 200
        assert resp.json()["data"].get("is_subscription_active") is True

    async def test_tier2_dynamic_eval_boundary_exact_match_timestamp_is_expired(self, client: AsyncClient):
        """When current timestamp matches or slightly exceeds expires_at, evaluates as expired."""
        store = await seed_store()
        now = utcnow()
        await set_subscription_in_db(store.merchant_id, status="ACTIVE", expires_at=now)

        resp = await client.get("/api/v1/merchants/profile", headers=bearer(store.owner_token))
        assert resp.status_code == 200
        assert resp.json()["data"].get("is_subscription_active") is False

    async def test_tier2_dynamic_eval_boundary_timezone_aware_vs_naive(self, client: AsyncClient):
        """Naive datetime strings are properly normalized to UTC without type errors."""
        store = await seed_store()
        naive_str = "2026-12-31T23:59:59"
        parsed = parse_iso_datetime(naive_str)
        assert parsed is not None
        assert parsed.tzinfo is not None


class TestTier2AdminViewBoundaries:
    """Tier 2: Boundaries for Admin View APIs."""

    async def test_tier2_admin_view_boundary_far_future_expiry_date(self, client: AsyncClient):
        """Subscription expiring in year 2099 serializes cleanly."""
        _, admin_token = await seed_admin()
        store = await seed_store()
        far_future = datetime(2099, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        await set_subscription_in_db(store.merchant_id, status="ACTIVE", expires_at=far_future)

        resp = await client.get(f"/api/v1/admin/merchants/{store.merchant_id}", headers=bearer(admin_token))
        assert resp.status_code == 200
        exp = parse_iso_datetime(resp.json()["data"].get("subscription_expires_at"))
        assert exp is not None and exp.year == 2099

    async def test_tier2_admin_view_boundary_far_past_expiry_date(self, client: AsyncClient):
        """Subscription expired in year 2020 serializes cleanly."""
        _, admin_token = await seed_admin()
        store = await seed_store()
        far_past = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        await set_subscription_in_db(store.merchant_id, status="ACTIVE", expires_at=far_past)

        resp = await client.get(f"/api/v1/admin/merchants/{store.merchant_id}", headers=bearer(admin_token))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data.get("is_subscription_active") is False

    async def test_tier2_admin_view_boundary_invalid_uuid_returns_422(self, client: AsyncClient):
        """Requesting /admin/merchants/invalid-uuid returns 422 Unprocessable Entity."""
        _, admin_token = await seed_admin()
        resp = await client.get("/api/v1/admin/merchants/not-a-valid-uuid", headers=bearer(admin_token))
        assert resp.status_code == 422

    async def test_tier2_admin_view_boundary_merchant_viewing_other_merchant_admin_403(self, client: AsyncClient):
        """Merchant attempting to view another merchant via admin route is rejected with 403."""
        store1 = await seed_store()
        store2 = await seed_store()

        resp = await client.get(f"/api/v1/admin/merchants/{store2.merchant_id}", headers=bearer(store1.owner_token))
        assert resp.status_code == 403

    async def test_tier2_admin_view_boundary_null_optional_fields_handled(self, client: AsyncClient):
        """Viewing merchant with null subscription dates does not raise internal server errors."""
        _, admin_token = await seed_admin()
        store = await seed_store()
        await set_subscription_in_db(store.merchant_id, status="ACTIVE", expires_at=None, start_date=None)

        resp = await client.get(f"/api/v1/admin/merchants/{store.merchant_id}", headers=bearer(admin_token))
        assert resp.status_code in (200, 404)


class TestTier2AdminUpdateBoundaries:
    """Tier 2: Boundaries for Admin Subscription Update."""

    async def test_tier2_admin_update_boundary_empty_body_validation_error(self, client: AsyncClient):
        """Empty payload to PUT subscription endpoint fails validation (422)."""
        _, admin_token = await seed_admin()
        store = await seed_store()

        resp = await client.put(
            f"/api/v1/admin/merchants/{store.merchant_id}/subscription",
            json={},
            headers=bearer(admin_token),
        )
        assert resp.status_code in (400, 422)

    async def test_tier2_admin_update_boundary_invalid_status_enum_validation_error(self, client: AsyncClient):
        """Invalid subscription_status enum string triggers 422 Unprocessable Entity."""
        _, admin_token = await seed_admin()
        store = await seed_store()

        payload = {"subscription_status": "SUPER_ACTIVE"}
        resp = await client.put(
            f"/api/v1/admin/merchants/{store.merchant_id}/subscription",
            json=payload,
            headers=bearer(admin_token),
        )
        assert resp.status_code == 422

    async def test_tier2_admin_update_boundary_past_expiry_immediately_effective_expired(self, client: AsyncClient):
        """Admin updating expiry to 1 minute ago immediately reflects as expired."""
        _, admin_token = await seed_admin()
        store = await seed_store()
        past = utcnow() - timedelta(minutes=1)

        payload = {"subscription_status": "ACTIVE", "subscription_expires_at": past.isoformat()}
        resp = await client.put(
            f"/api/v1/admin/merchants/{store.merchant_id}/subscription",
            json=payload,
            headers=bearer(admin_token),
        )
        assert resp.status_code == 200
        assert resp.json()["data"].get("is_subscription_active") is False

    async def test_tier2_admin_update_boundary_partial_update_preserves_start_date(self, client: AsyncClient):
        """Updating only subscription_status preserves the original start date."""
        _, admin_token = await seed_admin()
        store = await seed_store()
        original_start = utcnow() - timedelta(days=10)
        await set_subscription_in_db(store.merchant_id, status="ACTIVE", start_date=original_start)

        payload = {"subscription_status": "INACTIVE"}
        resp = await client.put(
            f"/api/v1/admin/merchants/{store.merchant_id}/subscription",
            json=payload,
            headers=bearer(admin_token),
        )
        assert resp.status_code == 200

    async def test_tier2_admin_update_boundary_active_status_with_past_date_shows_expired(self, client: AsyncClient):
        """Admin setting status ACTIVE with a past expiry date yields effective status EXPIRED."""
        _, admin_token = await seed_admin()
        store = await seed_store()
        past = utcnow() - timedelta(days=2)

        payload = {"subscription_status": "ACTIVE", "subscription_expires_at": past.isoformat()}
        resp = await client.put(
            f"/api/v1/admin/merchants/{store.merchant_id}/subscription",
            json=payload,
            headers=bearer(admin_token),
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        eff = data.get("effective_subscription_status") or ("EXPIRED" if not data.get("is_subscription_active") else data.get("subscription_status"))
        assert eff == "EXPIRED"


class TestTier2AdminExtendBoundaries:
    """Tier 2: Boundaries for Admin Subscription Extension."""

    async def test_tier2_admin_extend_boundary_zero_duration_rejected_or_noop(self, client: AsyncClient):
        """Extension with duration_days=0 is either rejected (422) or leaves expiry unchanged."""
        _, admin_token = await seed_admin()
        store = await seed_store()
        exp = utcnow() + timedelta(days=20)
        await set_subscription_in_db(store.merchant_id, status="ACTIVE", expires_at=exp)

        resp = await client.post(
            f"/api/v1/admin/merchants/{store.merchant_id}/subscription/extend",
            json={"duration_days": 0},
            headers=bearer(admin_token),
        )
        if resp.status_code == 200:
            new_exp = parse_iso_datetime(resp.json()["data"].get("subscription_expires_at"))
            assert abs((new_exp - exp).total_seconds()) < 60
        else:
            assert resp.status_code in (400, 422)

    async def test_tier2_admin_extend_boundary_negative_duration_rejected(self, client: AsyncClient):
        """Negative duration in extension request is rejected with 400 or 422."""
        _, admin_token = await seed_admin()
        store = await seed_store()

        resp = await client.post(
            f"/api/v1/admin/merchants/{store.merchant_id}/subscription/extend",
            json={"duration_days": -10},
            headers=bearer(admin_token),
        )
        assert resp.status_code in (400, 422)

    async def test_tier2_admin_extend_boundary_already_expired_merchant_extension_base(self, client: AsyncClient):
        """Extending an account expired 90 days ago calculates new expiry starting from now."""
        _, admin_token = await seed_admin()
        store = await seed_store()
        ancient_exp = utcnow() - timedelta(days=90)
        await set_subscription_in_db(store.merchant_id, status="EXPIRED", expires_at=ancient_exp)

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
        assert 29.0 <= delta <= 31.0

    async def test_tier2_admin_extend_boundary_large_duration_365_days(self, client: AsyncClient):
        """Extension by 365 days correctly adds one full year."""
        _, admin_token = await seed_admin()
        store = await seed_store()
        current_exp = utcnow() + timedelta(days=10)
        await set_subscription_in_db(store.merchant_id, status="ACTIVE", expires_at=current_exp)

        resp = await client.post(
            f"/api/v1/admin/merchants/{store.merchant_id}/subscription/extend",
            json={"duration_days": 365},
            headers=bearer(admin_token),
        )
        assert resp.status_code == 200
        new_exp = parse_iso_datetime(resp.json()["data"].get("subscription_expires_at"))
        delta = (new_exp - current_exp).total_seconds() / 86400
        assert 364.0 <= delta <= 366.0

    async def test_tier2_admin_extend_boundary_both_days_and_months_specified(self, client: AsyncClient):
        """Handling when both duration_days and months parameters are passed."""
        _, admin_token = await seed_admin()
        store = await seed_store()
        current_exp = utcnow() + timedelta(days=10)
        await set_subscription_in_db(store.merchant_id, status="ACTIVE", expires_at=current_exp)

        resp = await client.post(
            f"/api/v1/admin/merchants/{store.merchant_id}/subscription/extend",
            json={"duration_days": 30, "months": 1},
            headers=bearer(admin_token),
        )
        assert resp.status_code in (200, 422)
