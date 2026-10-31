"""Adversarial challenge and stress-test suite for Milestone 1 (Backend Subscription Model).

Empirically verifies:
1. Clock shifts & boundary limits: now - 1s, exact now, now + 1s, microsecond deltas.
2. Timezone permutations: Aware UTC, aware IST, extreme offsets, naive SQLite, ISO strings (Z / no-Z).
3. Unpersisted vs Flushed vs Committed Merchant instances.
4. Stress-test Pydantic MerchantOut.model_validate against edge cases.
5. Idempotent onboarding trial stability: ensures repeated calls never extend or reset trial date.
"""
import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, delete

from app.core.database import async_session_factory
from app.core.time_utils import IST
from app.main import app
from app.models.merchant import (
    KycStatus,
    Merchant,
    Sector,
    SubscriptionStatus,
    as_aware,
)
from app.models.system_settings import SystemSetting
from app.models.user import User, UserRole
from app.schemas.merchant import MerchantOut
from tests.feature_helpers import prepare_schema, seed_store, unique_phone


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _login_merchant(c: AsyncClient, phone: str) -> dict:
    send = await c.post("/api/v1/auth/otp/send", json={"phone": phone, "role": "merchant"})
    assert send.status_code == 200
    otp = send.json()["data"]["test_otp"]
    ver = await c.post("/api/v1/auth/otp/verify", json={"phone": phone, "otp": otp, "role": "merchant", "preferred_language": "en"})
    assert ver.status_code == 200
    return ver.json()["data"]


# ==============================================================================
# 1. Clock shifts and boundary limits
# ==============================================================================

def test_adv_boundary_exact_now():
    now = datetime.now(timezone.utc)
    m = Merchant(subscription_status=SubscriptionStatus.ACTIVE, subscription_expires_at=now)
    assert m.is_subscription_active is False
    assert m.effective_subscription_status == "EXPIRED"


def test_adv_boundary_transitions_past_and_future():
    now = datetime.now(timezone.utc)
    # 1 second past
    m_past_1s = Merchant(subscription_status=SubscriptionStatus.ACTIVE, subscription_expires_at=now - timedelta(seconds=1))
    assert m_past_1s.is_subscription_active is False
    assert m_past_1s.effective_subscription_status == "EXPIRED"

    # 1 microsecond past
    m_past_us = Merchant(subscription_status=SubscriptionStatus.ACTIVE, subscription_expires_at=now - timedelta(microseconds=1))
    assert m_past_us.is_subscription_active is False
    assert m_past_us.effective_subscription_status == "EXPIRED"

    # 1 second future
    m_fut_1s = Merchant(subscription_status=SubscriptionStatus.ACTIVE, subscription_expires_at=now + timedelta(seconds=1))
    assert m_fut_1s.is_subscription_active is True
    assert m_fut_1s.effective_subscription_status == "ACTIVE"

    # 100 milliseconds future
    m_fut_ms = Merchant(subscription_status=SubscriptionStatus.ACTIVE, subscription_expires_at=now + timedelta(milliseconds=100))
    assert m_fut_ms.is_subscription_active is True
    assert m_fut_ms.effective_subscription_status == "ACTIVE"


def test_adv_boundary_status_overrides():
    now = datetime.now(timezone.utc)
    # INACTIVE overrides both future and past expiration
    m_inact_fut = Merchant(subscription_status=SubscriptionStatus.INACTIVE, subscription_expires_at=now + timedelta(days=365))
    assert m_inact_fut.is_subscription_active is False
    assert m_inact_fut.effective_subscription_status == "INACTIVE"

    m_inact_past = Merchant(subscription_status=SubscriptionStatus.INACTIVE, subscription_expires_at=now - timedelta(days=365))
    assert m_inact_past.is_subscription_active is False
    assert m_inact_past.effective_subscription_status == "INACTIVE"

    # EXPIRED overrides future expiration
    m_exp_fut = Merchant(subscription_status=SubscriptionStatus.EXPIRED, subscription_expires_at=now + timedelta(days=365))
    assert m_exp_fut.is_subscription_active is False
    assert m_exp_fut.effective_subscription_status == "EXPIRED"


def test_adv_boundary_none_expiry():
    m_active_none = Merchant(subscription_status=SubscriptionStatus.ACTIVE, subscription_expires_at=None)
    assert m_active_none.is_subscription_active is True
    assert m_active_none.effective_subscription_status == "ACTIVE"

    m_inact_none = Merchant(subscription_status=SubscriptionStatus.INACTIVE, subscription_expires_at=None)
    assert m_inact_none.is_subscription_active is False
    assert m_inact_none.effective_subscription_status == "INACTIVE"


# ==============================================================================
# 2. Timezone permutations
# ==============================================================================

def test_adv_tz_aware_utc_and_ist():
    now_utc = datetime.now(timezone.utc)
    now_ist = datetime.now(IST)

    # Future IST
    m_ist_fut = Merchant(subscription_status=SubscriptionStatus.ACTIVE, subscription_expires_at=now_ist + timedelta(hours=1))
    assert m_ist_fut.is_subscription_active is True
    assert m_ist_fut.effective_subscription_status == "ACTIVE"

    # Past IST
    m_ist_past = Merchant(subscription_status=SubscriptionStatus.ACTIVE, subscription_expires_at=now_ist - timedelta(hours=1))
    assert m_ist_past.is_subscription_active is False
    assert m_ist_past.effective_subscription_status == "EXPIRED"


def test_adv_tz_extreme_offsets():
    # Line Islands UTC+14
    tz_plus14 = timezone(timedelta(hours=14))
    m_plus14_past = Merchant(subscription_status=SubscriptionStatus.ACTIVE, subscription_expires_at=datetime.now(tz_plus14) - timedelta(minutes=5))
    assert m_plus14_past.is_subscription_active is False
    assert m_plus14_past.effective_subscription_status == "EXPIRED"

    # Baker Island UTC-12
    tz_minus12 = timezone(timedelta(hours=-12))
    m_minus12_fut = Merchant(subscription_status=SubscriptionStatus.ACTIVE, subscription_expires_at=datetime.now(tz_minus12) + timedelta(minutes=5))
    assert m_minus12_fut.is_subscription_active is True
    assert m_minus12_fut.effective_subscription_status == "ACTIVE"


def test_adv_tz_iso_strings_permutations():
    # ISO strings with 'Z'
    parsed_z = as_aware("2030-01-01T00:00:00Z")
    assert parsed_z is not None and parsed_z.tzinfo == timezone.utc

    # ISO strings with '+00:00'
    parsed_zero = as_aware("2030-01-01T00:00:00+00:00")
    assert parsed_zero is not None and parsed_zero.tzinfo == timezone.utc

    # ISO strings with '+05:30'
    parsed_ist = as_aware("2030-01-01T00:00:00+05:30")
    assert parsed_ist is not None and parsed_ist.utcoffset() == timedelta(hours=5, minutes=30)

    # Naive ISO strings with space or T
    parsed_naive_t = as_aware("2030-01-01T00:00:00")
    assert parsed_naive_t is not None and parsed_naive_t.tzinfo == timezone.utc

    parsed_naive_space = as_aware("2030-01-01 00:00:00")
    assert parsed_naive_space is not None and parsed_naive_space.tzinfo == timezone.utc

    # ISO with fractional seconds
    parsed_us = as_aware("2030-01-01T00:00:00.654321Z")
    assert parsed_us is not None and parsed_us.microsecond == 654321


def test_adv_as_aware_edge_cases():
    assert as_aware(None) is None
    assert as_aware("invalid-date-string") is None
    assert as_aware("") is None
    assert as_aware("9999-99-99") is None


# ==============================================================================
# 3. Unpersisted vs Flushed vs Committed Merchant instances
# ==============================================================================

@pytest.mark.asyncio
async def test_adv_merchant_lifecycle_unpersisted_flushed_committed():
    await prepare_schema()

    # 1. Unpersisted instance
    u_id = uuid.uuid4()
    m = Merchant(
        id=uuid.uuid4(),
        user_id=u_id,
        business_name="Unpersisted Store",
        sector=Sector.FOOD,
        address_text="123 Test St",
        city="Pune",
        latitude=18.52,
        longitude=73.85,
        kyc_status=KycStatus.PENDING,
        kyc_doc_url="https://res.cloudinary.com/test.jpg",
    )
    assert m.effective_subscription_status == "ACTIVE"
    assert m.is_subscription_active is True
    # Model validate handles unpersisted instance without crash
    dto_unpersisted = MerchantOut.model_validate(m)
    assert dto_unpersisted.subscription_status == "ACTIVE"
    assert dto_unpersisted.is_subscription_active is True

    # 2. Flushed instance
    async with async_session_factory() as s:
        user = User(id=u_id, phone=unique_phone(), role=UserRole.MERCHANT)
        s.add(user)
        await s.flush()

        s.add(m)
        await s.flush()
        # subscription_status and subscription_start_date are set by model defaults on flush.
        assert m.subscription_status == SubscriptionStatus.ACTIVE
        assert m.subscription_start_date is not None
        # subscription_expires_at is intentionally None here: the model default is None.
        # The service layer (API onboarding endpoint) sets the expiry based on dynamic
        # system settings (auto_trial_enabled / auto_trial_duration_days). Direct DB
        # inserts that bypass the service layer reflect None (indefinite active trial).
        # effective_subscription_status treats ACTIVE + None expiry as ACTIVE (no expiry set).
        assert m.is_subscription_active is True

        await s.commit()

    # 3. Committed & re-queried instance
    async with async_session_factory() as s:
        reloaded = (await s.execute(select(Merchant).where(Merchant.id == m.id))).scalar_one()
        assert reloaded.is_subscription_active is True
        assert reloaded.effective_subscription_status == "ACTIVE"
        dto_committed = MerchantOut.model_validate(reloaded)
        assert dto_committed.subscription_status == "ACTIVE"
        assert dto_committed.is_subscription_active is True


# ==============================================================================
# 4. Stress-test Pydantic MerchantOut.model_validate against edge cases
# ==============================================================================

def test_adv_pydantic_alias_precedence_and_overrides():
    m_id = uuid.uuid4()
    base_dict = {
        "id": m_id,
        "business_name": "Test Store",
        "sector": "FOOD",
        "address_text": "123 Main Street",
        "city": "Pune",
        "latitude": 18.52,
        "longitude": 73.85,
        "kyc_status": "APPROVED",
    }

    # Case A: Both effective_subscription_status and subscription_status present (effective wins)
    d_both = {**base_dict, "effective_subscription_status": "EXPIRED", "subscription_status": "ACTIVE"}
    out_both = MerchantOut.model_validate(d_both)
    assert out_both.subscription_status == "EXPIRED"

    # Case B: Only subscription_status present
    d_single = {**base_dict, "subscription_status": "INACTIVE"}
    out_single = MerchantOut.model_validate(d_single)
    assert out_single.subscription_status == "INACTIVE"

    # Case C: Neither present (defaults to ACTIVE)
    out_default = MerchantOut.model_validate(base_dict)
    assert out_default.subscription_status == "ACTIVE"


def test_adv_pydantic_dynamic_orm_mapping_and_json_safety():
    now = datetime.now(timezone.utc)
    m = Merchant(
        id=uuid.uuid4(),
        business_name="Dynamic Store",
        sector=Sector.FOOD,
        address_text="123 Main Street",
        city="Pune",
        latitude=18.52,
        longitude=73.85,
        kyc_status=KycStatus.APPROVED,
        kyc_doc_url="https://res.cloudinary.com/test.jpg",
        subscription_status=SubscriptionStatus.ACTIVE,
        subscription_expires_at=now - timedelta(minutes=10),
    )
    dto = MerchantOut.model_validate(m)
    assert dto.subscription_status == "EXPIRED"
    assert dto.is_subscription_active is False

    # Check dump dictionary & json string serialization
    dumped = dto.model_dump()
    assert dumped["subscription_status"] == "EXPIRED"
    assert "effective_subscription_status" not in dumped

    json_str = dto.model_dump_json()
    assert '"subscription_status":"EXPIRED"' in json_str


# ==============================================================================
# 5. Idempotent onboarding trial stability
# ==============================================================================

@pytest.mark.asyncio
async def test_adv_idempotent_onboard_no_trial_extension_or_resurrection(client: AsyncClient):
    await prepare_schema()
    phone = unique_phone()
    auth = await _login_merchant(client, phone)
    headers = {"Authorization": f"Bearer {auth['access_token']}"}

    payload = {
        "business_name": "Idempotent Store",
        "sector": "FOOD",
        "address_text": "123 Main Street",
        "city": "Pune",
        "latitude": 18.52,
        "longitude": 73.85,
        "kyc_doc_url": "https://res.cloudinary.com/test.jpg",
    }

    # 1. Initial onboard
    res1 = await client.post("/api/v1/merchants/onboard", headers=headers, json=payload)
    assert res1.status_code == 200
    data1 = res1.json()["data"]
    assert data1["subscription_status"] == "ACTIVE"
    assert data1["is_subscription_active"] is True
    exp1 = data1["subscription_expires_at"]
    start1 = data1["subscription_start_date"]

    # 2. Immediate second call (idempotent retry)
    res2 = await client.post("/api/v1/merchants/onboard", headers=headers, json=payload)
    assert res2.status_code == 200
    data2 = res2.json()["data"]
    assert data2["subscription_status"] == "ACTIVE"
    # Timestamps must NOT shift or advance
    assert data2["subscription_expires_at"] == exp1
    assert data2["subscription_start_date"] == start1

    # 3. Simulate subscription expiration in DB: verify retry does NOT revive trial
    async with async_session_factory() as s:
        merchant = await s.get(Merchant, uuid.UUID(data1["id"]))
        assert merchant is not None
        merchant.subscription_status = SubscriptionStatus.EXPIRED
        merchant.subscription_expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        await s.commit()

    res3 = await client.post("/api/v1/merchants/onboard", headers=headers, json=payload)
    assert res3.status_code == 200
    data3 = res3.json()["data"]
    # Must preserve EXPIRED status and not grant another 90 days
    assert data3["subscription_status"] == "EXPIRED"
    assert data3["is_subscription_active"] is False


@pytest.mark.asyncio
async def test_adv_legacy_merchant_self_heal_stability(client: AsyncClient):
    await prepare_schema()
    phone = unique_phone()
    auth = await _login_merchant(client, phone)
    headers = {"Authorization": f"Bearer {auth['access_token']}"}

    # Ensure auto-trial is enabled with 90-day default so self-heal sets expires_at
    async with async_session_factory() as s:
        await s.execute(delete(SystemSetting))
        await s.commit()

    # Reset the existing merchant record to simulate a legacy NULL-status record.
    # (login creates a merchant via OTP verify flow; we reset it to NULL fields here)
    async with async_session_factory() as s:
        from sqlalchemy import update
        from app.models.merchant import Merchant as M
        await s.execute(
            update(M)
            .where(M.user_id == uuid.UUID(auth["user"]["id"]))
            .values(
                subscription_status=None,
                subscription_start_date=None,
                subscription_expires_at=None,
            )
        )
        await s.commit()

    payload = {
        "business_name": "Legacy Store",
        "sector": "FOOD",
        "address_text": "123 Legacy Road",
        "city": "Pune",
        "latitude": 18.52,
        "longitude": 73.85,
        "kyc_doc_url": "https://res.cloudinary.com/test.jpg",
    }

    # First call: heals null fields — auto trial is enabled so expires_at is set
    res1 = await client.post("/api/v1/merchants/onboard", headers=headers, json=payload)
    assert res1.status_code == 200
    d1 = res1.json()["data"]
    assert d1["subscription_status"] == "ACTIVE"
    assert d1["is_subscription_active"] is True
    healed_exp = d1["subscription_expires_at"]
    assert healed_exp is not None

    # Second call: must retain healed timestamps without modification
    res2 = await client.post("/api/v1/merchants/onboard", headers=headers, json=payload)
    assert res2.status_code == 200
    d2 = res2.json()["data"]
    assert d2["subscription_expires_at"] == healed_exp
