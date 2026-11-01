"""Tests for 10-Minute Redemption Session Token and Merchant Owner Scanning Flow."""
import uuid
from datetime import datetime, timezone, timedelta
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.core.database import async_session_factory
from app.models.coupon import CouponStatus, CouponTemplate, DiscountType, RedemptionsLedger, UserCoupon
from app.models.merchant import KycStatus, Merchant, MerchantStaff, Sector
from app.models.reel import Reel, ReelStatus
from app.models.user import User, UserRole
from app.services.totp import TotpService
from app.services.redemption_service import RedemptionService
from tests.feature_helpers import (
    bearer,
    prepare_schema,
    seed_store,
    seed_user,
)


@pytest_asyncio.fixture(autouse=True)
async def init_db():
    await prepare_schema()
    yield


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def create_test_coupon(merchant_id: uuid.UUID, shopper_id: uuid.UUID):
    async with async_session_factory() as session:
        reel = Reel(
            merchant_id=merchant_id,
            title="Scan Promo Reel",
            video_url="http://test.com/vid.mp4",
            thumbnail_url="http://test.com/thumb.jpg",
            duration_seconds=15,
            status=ReelStatus.APPROVED,
        )
        session.add(reel)
        await session.flush()

        tmpl = CouponTemplate(
            merchant_id=merchant_id,
            reel_id=reel.id,
            title="FLAT 100 OFF",
            discount_type=DiscountType.FLAT_AMOUNT,
            discount_value=100,
            min_order_amount=300,
            validity_days=7,
        )
        session.add(tmpl)
        await session.flush()

        totp_sec = TotpService.generate_secret()
        uc = UserCoupon(
            coupon_template_id=tmpl.id,
            user_id=shopper_id,
            status=CouponStatus.CLAIMED,
            totp_secret=totp_sec,
            expires_at=datetime.now(timezone.utc) + timedelta(days=5),
        )
        session.add(uc)
        await session.commit()
        return uc.id, totp_sec, tmpl.id


@pytest.mark.asyncio
async def test_preview_generates_session_token(client: AsyncClient):
    store = await seed_store(with_staff=True)
    shopper_id, _ = await seed_user("SHOPPER", "Shopper A")
    uc_id, secret, _ = await create_test_coupon(store.merchant_id, shopper_id)

    qr_payload, _, _, _ = TotpService.generate_dynamic_qr_payload(uc_id, secret, shopper_id)

    resp = await client.post(
        "/api/v1/redemptions/preview",
        headers=bearer(store.staff_token),
        json={"qr_payload": qr_payload},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["session_token"] is not None
    assert isinstance(data["session_token"], str)
    assert len(data["session_token"]) > 20
    assert data["coupon_title"] == "FLAT 100 OFF"


@pytest.mark.asyncio
async def test_verify_and_redeem_with_session_token(client: AsyncClient):
    store = await seed_store(with_staff=True)
    shopper_id, _ = await seed_user("SHOPPER", "Shopper B")
    uc_id, secret, _ = await create_test_coupon(store.merchant_id, shopper_id)

    qr_payload, _, _, _ = TotpService.generate_dynamic_qr_payload(uc_id, secret, shopper_id)

    # 1. Preview
    prev_resp = await client.post(
        "/api/v1/redemptions/preview",
        headers=bearer(store.staff_token),
        json={"qr_payload": qr_payload},
    )
    assert prev_resp.status_code == 200
    session_token = prev_resp.json()["data"]["session_token"]

    # 2. Verify with session token (without qr_payload)
    verify_resp = await client.post(
        "/api/v1/redemptions/verify",
        headers=bearer(store.staff_token),
        json={
            "session_token": session_token,
            "bill_amount": 500.0,
        },
    )
    assert verify_resp.status_code == 200, verify_resp.text
    res_data = verify_resp.json()["data"]
    assert res_data["status"] == "VERIFIED_AND_REDEEMED"
    assert res_data["discount_applied"] == 100.0

    # 3. Double-spend prevention with same session token
    dup_resp = await client.post(
        "/api/v1/redemptions/verify",
        headers=bearer(store.staff_token),
        json={
            "session_token": session_token,
            "bill_amount": 500.0,
        },
    )
    assert dup_resp.status_code == 409


@pytest.mark.asyncio
async def test_merchant_owner_can_scan_preview_and_redeem(client: AsyncClient):
    store = await seed_store(with_staff=False)
    shopper_id, _ = await seed_user("SHOPPER", "Shopper C")
    uc_id, secret, _ = await create_test_coupon(store.merchant_id, shopper_id)

    qr_payload, _, _, _ = TotpService.generate_dynamic_qr_payload(uc_id, secret, shopper_id)

    # Merchant owner previews QR
    prev_resp = await client.post(
        "/api/v1/redemptions/preview",
        headers=bearer(store.owner_token),
        json={"qr_payload": qr_payload},
    )
    assert prev_resp.status_code == 200, prev_resp.text
    session_token = prev_resp.json()["data"]["session_token"]

    # Merchant owner verifies and redeems
    verify_resp = await client.post(
        "/api/v1/redemptions/verify",
        headers=bearer(store.owner_token),
        json={
            "session_token": session_token,
            "bill_amount": 450.0,
        },
    )
    assert verify_resp.status_code == 200, verify_resp.text
    res_data = verify_resp.json()["data"]
    assert res_data["status"] == "VERIFIED_AND_REDEEMED"

    # Verify staff_id is None in ledger
    async with async_session_factory() as session:
        ledger = await session.get(RedemptionsLedger, uuid.UUID(res_data["redemption_id"]))
        assert ledger is not None
        assert ledger.staff_id is None
        assert ledger.merchant_id == store.merchant_id


@pytest.mark.asyncio
async def test_session_token_cross_merchant_rejected(client: AsyncClient):
    store_a = await seed_store(with_staff=True)
    store_b = await seed_store(with_staff=True)
    shopper_id, _ = await seed_user("SHOPPER", "Shopper D")
    uc_id, secret, _ = await create_test_coupon(store_a.merchant_id, shopper_id)

    # Generate session token bound to store A
    session_token = RedemptionService.create_redemption_session(uc_id, store_a.merchant_id)

    # Store B tries to redeem
    resp = await client.post(
        "/api/v1/redemptions/verify",
        headers=bearer(store_b.staff_token),
        json={
            "session_token": session_token,
            "bill_amount": 500.0,
        },
    )
    assert resp.status_code == 403
    err_msg = resp.json().get("error", {}).get("message", "")
    assert "different merchant" in err_msg.lower()


@pytest.mark.asyncio
async def test_expired_session_token_returns_410(client: AsyncClient):
    store = await seed_store(with_staff=True)
    shopper_id, _ = await seed_user("SHOPPER", "Shopper E")
    uc_id, secret, _ = await create_test_coupon(store.merchant_id, shopper_id)

    # Generate an already-expired session token
    from app.core.security import create_access_token
    expired_token = create_access_token(
        subject=str(uc_id),
        role="redemption_session",
        extra_claims={
            "token_type": "redemption_session",
            "claim_id": str(uc_id),
            "merchant_id": str(store.merchant_id),
        },
        expires_delta=timedelta(seconds=-5),
    )

    resp = await client.post(
        "/api/v1/redemptions/verify",
        headers=bearer(store.staff_token),
        json={"session_token": expired_token, "bill_amount": 500.0},
    )
    assert resp.status_code == 410, resp.text
    detail = resp.json().get("detail") or resp.json().get("error", {}).get("message", "")
    assert "expired" in detail.lower()


@pytest.mark.asyncio
async def test_malformed_session_token_returns_400(client: AsyncClient):
    store = await seed_store(with_staff=True)
    resp = await client.post(
        "/api/v1/redemptions/verify",
        headers=bearer(store.staff_token),
        json={"session_token": "not.a.valid.jwt", "bill_amount": 500.0},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_verify_without_session_token_or_qr_payload_returns_400(client: AsyncClient):
    store = await seed_store(with_staff=True)
    resp = await client.post(
        "/api/v1/redemptions/verify",
        headers=bearer(store.staff_token),
        json={"bill_amount": 500.0},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_merchant_user_without_merchant_profile_returns_404(client: AsyncClient):
    orphan_user_id, orphan_token = await seed_user("MERCHANT", "Orphan Merchant")
    resp = await client.post(
        "/api/v1/redemptions/preview",
        headers=bearer(orphan_token),
        json={"qr_payload": "some-code"},
    )
    assert resp.status_code == 404

