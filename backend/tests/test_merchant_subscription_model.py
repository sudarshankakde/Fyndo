"""Comprehensive unit and integration tests for Merchant Subscription Model (Milestone 1)."""
import uuid
from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import select

from app.core.database import async_session_factory
from app.core.time_utils import IST
from app.models.merchant import (
    KycStatus,
    Merchant,
    Sector,
    SubscriptionStatus,
    as_aware,
)
from app.schemas.merchant import MerchantOut
from tests.feature_helpers import prepare_schema, seed_store, unique_phone


@pytest.fixture(autouse=True)
async def auto_prepare_schema():
    await prepare_schema()


def test_subscription_status_enum():
    assert SubscriptionStatus.ACTIVE == "ACTIVE"
    assert SubscriptionStatus.INACTIVE == "INACTIVE"
    assert SubscriptionStatus.EXPIRED == "EXPIRED"
    assert SubscriptionStatus("ACTIVE") == SubscriptionStatus.ACTIVE
    assert SubscriptionStatus("INACTIVE") == SubscriptionStatus.INACTIVE
    assert SubscriptionStatus("EXPIRED") == SubscriptionStatus.EXPIRED
    with pytest.raises(ValueError):
        SubscriptionStatus("UNKNOWN_STATUS")


def test_merchant_default_properties():
    merchant = Merchant(
        business_name="Unpersisted Store",
        sector=Sector.FOOD,
        address_text="123 Test St",
        city="Nagpur",
        latitude=21.14,
        longitude=79.08,
        kyc_doc_url="https://test.com/doc.pdf",
    )
    assert merchant.is_subscription_active is True
    assert merchant.effective_subscription_status == "ACTIVE"


def test_active_with_future_expiry():
    future = datetime.now(timezone.utc) + timedelta(days=45)
    merchant = Merchant(
        subscription_status=SubscriptionStatus.ACTIVE,
        subscription_expires_at=future,
    )
    assert merchant.is_subscription_active is True
    assert merchant.effective_subscription_status == "ACTIVE"


def test_dynamic_expiration_with_past_expiry():
    past = datetime.now(timezone.utc) - timedelta(minutes=5)
    merchant = Merchant(
        subscription_status=SubscriptionStatus.ACTIVE,
        subscription_expires_at=past,
    )
    assert merchant.is_subscription_active is False
    assert merchant.effective_subscription_status == "EXPIRED"


def test_inactive_overrides_future_expiry():
    future = datetime.now(timezone.utc) + timedelta(days=90)
    merchant = Merchant(
        subscription_status=SubscriptionStatus.INACTIVE,
        subscription_expires_at=future,
    )
    assert merchant.is_subscription_active is False
    assert merchant.effective_subscription_status == "INACTIVE"


def test_explicit_expired_status():
    future = datetime.now(timezone.utc) + timedelta(days=30)
    merchant = Merchant(
        subscription_status=SubscriptionStatus.EXPIRED,
        subscription_expires_at=future,
    )
    assert merchant.is_subscription_active is False
    assert merchant.effective_subscription_status == "EXPIRED"


def test_as_aware_helper():
    assert as_aware(None) is None

    # Naive datetime normalized to UTC aware
    naive = datetime(2026, 1, 1, 10, 0, 0)
    aware = as_aware(naive)
    assert aware is not None
    assert aware.tzinfo == timezone.utc
    assert aware.year == 2026

    # Aware datetime preserved
    ist_dt = datetime.now(IST)
    preserved = as_aware(ist_dt)
    assert preserved.tzinfo == IST

    # ISO string parsing
    parsed_utc = as_aware("2026-10-29T12:00:00Z")
    assert parsed_utc is not None
    assert parsed_utc.tzinfo == timezone.utc

    # Malformed string
    assert as_aware("invalid-date") is None


def test_sqlite_naive_datetime_comparisons():
    # Naive past datetime
    naive_past = datetime(2020, 1, 1, 0, 0, 0)
    m_past = Merchant(
        subscription_status=SubscriptionStatus.ACTIVE,
        subscription_expires_at=naive_past,
    )
    assert m_past.is_subscription_active is False
    assert m_past.effective_subscription_status == "EXPIRED"

    # Naive future datetime
    naive_future = datetime(2099, 12, 31, 23, 59, 59)
    m_future = Merchant(
        subscription_status=SubscriptionStatus.ACTIVE,
        subscription_expires_at=naive_future,
    )
    assert m_future.is_subscription_active is True
    assert m_future.effective_subscription_status == "ACTIVE"


def test_models_export_subscription_status():
    import app.models as models

    assert hasattr(models, "SubscriptionStatus")
    assert "SubscriptionStatus" in models.__all__
    assert models.SubscriptionStatus.ACTIVE == "ACTIVE"


def test_merchant_out_schema_serialization_active():
    now = datetime.now(timezone.utc)
    merchant = Merchant(
        id=uuid.uuid4(),
        business_name="Active Store",
        sector=Sector.FOOD,
        address_text="123 Main St",
        city="Nagpur",
        latitude=21.14,
        longitude=79.08,
        kyc_status=KycStatus.APPROVED,
        kyc_doc_url="https://test.com/doc.pdf",
        call_clicks_count=0,
        subscription_status=SubscriptionStatus.ACTIVE,
        subscription_start_date=now,
        subscription_expires_at=now + timedelta(days=90),
    )
    dto = MerchantOut.model_validate(merchant)
    assert dto.subscription_status == "ACTIVE"
    assert dto.is_subscription_active is True
    assert dto.subscription_start_date == merchant.subscription_start_date
    assert dto.subscription_expires_at == merchant.subscription_expires_at
    dumped = dto.model_dump()
    assert "subscription_status" in dumped
    assert "effective_subscription_status" not in dumped


def test_merchant_out_schema_dynamic_expiration_mapping():
    now = datetime.now(timezone.utc)
    # Status column is ACTIVE, but expiration timestamp passed
    merchant = Merchant(
        id=uuid.uuid4(),
        business_name="Expired Store",
        sector=Sector.FOOD,
        address_text="123 Main St",
        city="Nagpur",
        latitude=21.14,
        longitude=79.08,
        kyc_status=KycStatus.APPROVED,
        kyc_doc_url="https://test.com/doc.pdf",
        call_clicks_count=0,
        subscription_status=SubscriptionStatus.ACTIVE,
        subscription_start_date=now - timedelta(days=91),
        subscription_expires_at=now - timedelta(days=1),
    )
    dto = MerchantOut.model_validate(merchant)
    assert dto.subscription_status == "EXPIRED"
    assert dto.is_subscription_active is False


@pytest.mark.asyncio
async def test_seed_store_subscription_defaults_and_db_persistence():
    store = await seed_store()
    async with async_session_factory() as session:
        merchant = await session.get(Merchant, store.merchant_id)
        assert merchant is not None
        assert merchant.subscription_status == SubscriptionStatus.ACTIVE
        assert merchant.is_subscription_active is True
        assert merchant.effective_subscription_status == "ACTIVE"
        assert merchant.subscription_start_date is not None
        assert merchant.subscription_expires_at is not None
        # Trial window is ~90 days
        diff = merchant.subscription_expires_at - merchant.subscription_start_date
        assert diff.days == 90


@pytest.mark.asyncio
async def test_seed_store_expired_override():
    past = datetime.now(timezone.utc) - timedelta(days=5)
    store = await seed_store(
        subscription_status=SubscriptionStatus.EXPIRED,
        subscription_expires_at=past,
    )
    async with async_session_factory() as session:
        merchant = await session.get(Merchant, store.merchant_id)
        assert merchant is not None
        assert merchant.subscription_status == SubscriptionStatus.EXPIRED
        assert merchant.is_subscription_active is False
        assert merchant.effective_subscription_status == "EXPIRED"


@pytest.mark.asyncio
async def test_admin_create_merchant_assigns_90_day_trial():
    from app.schemas.admin import AdminMerchantCreateRequest
    from app.services.admin_service import AdminService

    req = AdminMerchantCreateRequest(
        business_name="Admin Quick Store",
        owner_phone=unique_phone(),
        sector="ELECTRONICS",
        address_text="FC Road, Pune",
        city="Pune",
        latitude=18.52,
        longitude=73.85,
    )
    before = datetime.now(timezone.utc)
    async with async_session_factory() as session:
        detail = await AdminService.create_merchant(req, session)
        await session.commit()

        merchant = (await session.execute(select(Merchant).where(Merchant.id == detail.id))).scalar_one()
        assert merchant.subscription_status == SubscriptionStatus.ACTIVE
        assert merchant.is_subscription_active is True
        assert merchant.effective_subscription_status == "ACTIVE"
        assert abs((merchant.subscription_start_date - before).total_seconds()) < 10
        assert (merchant.subscription_expires_at - merchant.subscription_start_date).days == 90
