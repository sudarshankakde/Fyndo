"""Tier 1 - Feature 1 & 2: Automatic 3-Month Trial & Dynamic Expiration Evaluation."""
from datetime import timedelta
import pytest
from httpx import AsyncClient

from tests.e2e_subscriptions.helpers import (
    bearer,
    onboard_merchant_via_api,
    parse_iso_datetime,
    seed_store,
    seed_user,
    set_subscription_in_db,
    utcnow,
)

pytestmark = pytest.mark.asyncio


class TestTier1SignupTrial:
    """Tier 1: Feature 1 - Automatic 3-Month Free Trial on Merchant Signup."""

    async def test_tier1_signup_assigns_active_status(self, client: AsyncClient):
        """Newly onboarded merchant automatically receives ACTIVE subscription status."""
        _, _, data = await onboard_merchant_via_api(client, business_name="Trial Status Store")
        assert data.get("success") is True, f"Onboard failed: {data}"
        merchant = data["data"]
        assert merchant.get("subscription_status") == "ACTIVE"

    async def test_tier1_signup_assigns_start_date(self, client: AsyncClient):
        """Newly onboarded merchant automatically receives subscription_start_date near now."""
        now = utcnow()
        _, _, data = await onboard_merchant_via_api(client, business_name="Trial Start Store")
        assert data.get("success") is True
        start_date = parse_iso_datetime(data["data"].get("subscription_start_date"))
        assert start_date is not None
        assert abs((start_date - now).total_seconds()) < 120

    async def test_tier1_signup_assigns_90day_trial_expiry(self, client: AsyncClient):
        """Newly onboarded merchant expiration date is configured for ~90 days in the future."""
        now = utcnow()
        _, _, data = await onboard_merchant_via_api(client, business_name="Trial Expiry Store")
        assert data.get("success") is True
        expires_at = parse_iso_datetime(data["data"].get("subscription_expires_at"))
        assert expires_at is not None
        delta_days = (expires_at - now).total_seconds() / 86400
        assert 89 <= delta_days <= 92, f"Expected ~90 days trial, got {delta_days} days"

    async def test_tier1_signup_marks_subscription_active_flag(self, client: AsyncClient):
        """Newly onboarded merchant has is_subscription_active evaluated as True."""
        _, _, data = await onboard_merchant_via_api(client, business_name="Trial Active Flag Store")
        assert data.get("success") is True
        assert data["data"].get("is_subscription_active") is True

    async def test_tier1_profile_endpoint_reflects_active_trial(self, client: AsyncClient):
        """GET /api/v1/merchants/profile reflects the active 3-month trial subscription."""
        _, token, onboard_data = await onboard_merchant_via_api(client, business_name="Trial Profile Store")
        assert onboard_data.get("success") is True

        resp = await client.get("/api/v1/merchants/profile", headers=bearer(token))
        assert resp.status_code == 200, resp.text
        profile = resp.json()["data"]
        assert profile.get("subscription_status") == "ACTIVE"
        assert profile.get("is_subscription_active") is True
        assert profile.get("subscription_expires_at") is not None


class TestTier1DynamicEval:
    """Tier 1: Feature 2 - Dynamic Expiration Evaluation Property."""

    async def test_tier1_dynamic_eval_active_when_future_expiry(self, client: AsyncClient):
        """Merchant with status ACTIVE and future expiration evaluates as active."""
        store = await seed_store()
        future = utcnow() + timedelta(days=30)
        await set_subscription_in_db(store.merchant_id, status="ACTIVE", expires_at=future)

        resp = await client.get("/api/v1/merchants/profile", headers=bearer(store.owner_token))
        assert resp.status_code == 200
        profile = resp.json()["data"]
        assert profile.get("is_subscription_active") is True
        assert profile.get("subscription_status") == "ACTIVE"

    async def test_tier1_dynamic_eval_expired_when_past_expiry(self, client: AsyncClient):
        """Merchant with past expiration date evaluates is_subscription_active as False."""
        store = await seed_store()
        past = utcnow() - timedelta(days=2)
        await set_subscription_in_db(store.merchant_id, status="ACTIVE", expires_at=past)

        resp = await client.get("/api/v1/merchants/profile", headers=bearer(store.owner_token))
        assert resp.status_code == 200
        profile = resp.json()["data"]
        assert profile.get("is_subscription_active") is False

    async def test_tier1_dynamic_eval_effective_status_reflects_expired(self, client: AsyncClient):
        """Merchant with status ACTIVE in DB but past expires_at evaluates effectively as EXPIRED."""
        store = await seed_store()
        past = utcnow() - timedelta(hours=1)
        await set_subscription_in_db(store.merchant_id, status="ACTIVE", expires_at=past)

        resp = await client.get("/api/v1/merchants/profile", headers=bearer(store.owner_token))
        assert resp.status_code == 200
        profile = resp.json()["data"]
        status = profile.get("effective_subscription_status") or profile.get("subscription_status")
        assert status == "EXPIRED"

    async def test_tier1_dynamic_eval_inactive_status_overrides_future_date(self, client: AsyncClient):
        """Merchant explicitly marked INACTIVE evaluates as not active even with future expires_at."""
        store = await seed_store()
        future = utcnow() + timedelta(days=60)
        await set_subscription_in_db(store.merchant_id, status="INACTIVE", expires_at=future)

        resp = await client.get("/api/v1/merchants/profile", headers=bearer(store.owner_token))
        assert resp.status_code == 200
        profile = resp.json()["data"]
        assert profile.get("is_subscription_active") is False
        assert profile.get("subscription_status") == "INACTIVE"

    async def test_tier1_dynamic_eval_utc_iso_timestamp_parsing(self, client: AsyncClient):
        """Dynamic evaluation handles ISO 8601 UTC timestamps consistently."""
        store = await seed_store()
        now = utcnow()
        await set_subscription_in_db(store.merchant_id, status="ACTIVE", expires_at=now + timedelta(days=1))

        resp = await client.get("/api/v1/merchants/profile", headers=bearer(store.owner_token))
        assert resp.status_code == 200
        expires_str = resp.json()["data"].get("subscription_expires_at")
        assert expires_str is not None
        parsed = parse_iso_datetime(expires_str)
        assert parsed is not None
        assert parsed > now
