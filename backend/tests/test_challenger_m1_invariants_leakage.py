"""Empirical Challenger Tests: Inactive Evaluation Invariant & Public API Leakage Prevention.

Adversarially validates:
3. INACTIVE status immediately blocks active evaluation even if expiry is 10 years in the future.
4. Public shopper schemas and endpoints (PublicMerchantOut, FollowedMerchantOut) NEVER leak subscription data.
"""
import uuid
from datetime import datetime, timedelta, timezone
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import async_session_factory
from app.main import app
from app.models.merchant import KycStatus, Merchant, Sector, SubscriptionStatus
from app.schemas.merchant import MerchantOut, PublicMerchantOut
from app.schemas.merchant_engagement import FollowedMerchantOut
from tests.e2e_subscriptions.helpers import bearer, seed_store, seed_user

pytestmark = pytest.mark.asyncio


class TestInactiveStatusOverride:
    """Challenge 3: INACTIVE status blocks active evaluation even with 10-year future expiry."""

    async def test_inactive_blocks_10_year_future_expiry_in_memory(self):
        """Merchant model with INACTIVE status and 10-year future expiry must evaluate as inactive."""
        future_10_years = datetime.now(timezone.utc) + timedelta(days=3650)
        merchant = Merchant(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            business_name="Long Term Inactive Store",
            sector=Sector.FOOD,
            address_text="Station Road",
            city="Nagpur",
            latitude=21.14,
            longitude=79.08,
            kyc_doc_url="https://doc.pdf",
            kyc_status=KycStatus.APPROVED,
            subscription_status=SubscriptionStatus.INACTIVE,
            subscription_start_date=datetime.now(timezone.utc),
            subscription_expires_at=future_10_years,
        )

        assert merchant.effective_subscription_status == "INACTIVE"
        assert merchant.is_subscription_active is False

        # Schema serialization must also reflect INACTIVE and is_subscription_active=False
        out = MerchantOut.model_validate(merchant)
        assert out.subscription_status == "INACTIVE"
        assert out.is_subscription_active is False

        dump = out.model_dump()
        assert dump["subscription_status"] == "INACTIVE"
        assert dump["is_subscription_active"] is False

    async def test_lowercase_inactive_string_handled(self):
        """String 'inactive' (lowercase) must be normalized and block active evaluation."""
        merchant = Merchant(
            business_name="Lowercase Inactive Store",
            subscription_status="inactive",
            subscription_expires_at=datetime.now(timezone.utc) + timedelta(days=3650),
        )
        assert merchant.effective_subscription_status == "INACTIVE"
        assert merchant.is_subscription_active is False

    async def test_explicit_expired_blocks_future_expiry(self):
        """Status EXPIRED with future expiry must report EXPIRED and False."""
        merchant = Merchant(
            business_name="Prematurely Expired Store",
            subscription_status=SubscriptionStatus.EXPIRED,
            subscription_expires_at=datetime.now(timezone.utc) + timedelta(days=3650),
        )
        assert merchant.effective_subscription_status == "EXPIRED"
        assert merchant.is_subscription_active is False

    async def test_db_persisted_inactive_merchant_profile_api(self):
        """DB-persisted merchant with INACTIVE status and 10-year expiry returns inactive on profile API."""
        store = await seed_store(
            subscription_status=SubscriptionStatus.INACTIVE,
            subscription_expires_at=datetime.now(timezone.utc) + timedelta(days=3650),
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/merchants/profile", headers=bearer(store.owner_token))
            assert resp.status_code == 200, resp.text
            data = resp.json()["data"]
            assert data["subscription_status"] == "INACTIVE"
            assert data["is_subscription_active"] is False


class TestPublicApiLeakagePrevention:
    """Challenge 4: Public shopper APIs never leak subscription data even if passed malicious payloads."""

    async def test_public_merchant_out_rejects_and_excludes_subscription_fields(self):
        """PublicMerchantOut schema must NOT include subscription keys even from untrusted dict."""
        malicious_input = {
            "id": uuid.uuid4(),
            "business_name": "Public Store",
            "sector": "FOOD",
            "address_text": "123 Market St",
            "city": "Nagpur",
            "latitude": 21.14,
            "longitude": 79.08,
            "subscription_status": "ACTIVE",
            "subscription_start_date": datetime.now(timezone.utc),
            "subscription_expires_at": datetime.now(timezone.utc) + timedelta(days=90),
            "is_subscription_active": True,
            "effective_subscription_status": "ACTIVE",
            "admin_secret_notes": "leak_attempt",
        }

        # Model validation
        public_obj = PublicMerchantOut.model_validate(malicious_input)

        # Attribute inspection
        assert not hasattr(public_obj, "subscription_status")
        assert not hasattr(public_obj, "subscription_expires_at")
        assert not hasattr(public_obj, "subscription_start_date")
        assert not hasattr(public_obj, "is_subscription_active")

        # Serialized dictionary and JSON verification
        dump = public_obj.model_dump()
        json_str = public_obj.model_dump_json()

        for key in dump.keys():
            assert "subscription" not in key.lower(), f"Leaked key in model_dump: {key}"

        assert "subscription" not in json_str.lower(), "Leaked subscription substring in model_dump_json"

    async def test_followed_merchant_out_excludes_subscription_fields(self):
        """FollowedMerchantOut schema must NOT include subscription keys from uncleaned dict."""
        malicious_input = {
            "id": uuid.uuid4(),
            "business_name": "Followed Store",
            "sector": "FOOD",
            "city": "Nagpur",
            "address_text": "123 Market St",
            "followed_at": datetime.now(timezone.utc),
            "subscription_status": "ACTIVE",
            "subscription_start_date": datetime.now(timezone.utc),
            "subscription_expires_at": datetime.now(timezone.utc) + timedelta(days=90),
            "is_subscription_active": True,
        }

        followed_obj = FollowedMerchantOut.model_validate(malicious_input)

        assert not hasattr(followed_obj, "subscription_status")
        assert not hasattr(followed_obj, "subscription_expires_at")
        assert not hasattr(followed_obj, "is_subscription_active")

        dump = followed_obj.model_dump()
        json_str = followed_obj.model_dump_json()

        for key in dump.keys():
            assert "subscription" not in key.lower(), f"Leaked key in model_dump: {key}"

        assert "subscription" not in json_str.lower(), "Leaked subscription substring in model_dump_json"

    async def test_live_public_merchant_endpoint_does_not_leak_subscription(self):
        """Live GET /api/v1/merchants/{id} endpoint payload must NOT contain any subscription keys."""
        store = await seed_store(
            subscription_status=SubscriptionStatus.ACTIVE,
            subscription_expires_at=datetime.now(timezone.utc) + timedelta(days=90),
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/api/v1/merchants/{store.merchant_id}")
            assert resp.status_code == 200, resp.text
            data = resp.json()["data"]

            for key in data.keys():
                assert "subscription" not in key.lower(), f"Public endpoint leaked key: {key}"

    async def test_live_followed_merchants_endpoint_does_not_leak_subscription(self):
        """Live GET /api/v1/merchants/following endpoint payload must NOT contain any subscription keys."""
        store = await seed_store(
            subscription_status=SubscriptionStatus.ACTIVE,
            subscription_expires_at=datetime.now(timezone.utc) + timedelta(days=90),
        )
        shopper_id, shopper_token = await seed_user("SHOPPER", "Shopper Follower")

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Follow merchant first
            follow_resp = await client.post(
                f"/api/v1/merchants/{store.merchant_id}/follow",
                headers=bearer(shopper_token),
            )
            assert follow_resp.status_code == 200, follow_resp.text

            # Retrieve following list
            resp = await client.get("/api/v1/merchants/following", headers=bearer(shopper_token))
            assert resp.status_code == 200, resp.text
            items = resp.json()["data"]
            assert len(items) >= 1

            for item in items:
                for key in item.keys():
                    assert "subscription" not in key.lower(), f"Followed endpoint leaked key: {key}"
