"""Tests for Cashier Backend Connection and Verified Badge Standard."""
import uuid
from datetime import datetime, timezone, timedelta
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.core.database import async_session_factory
from app.models.coupon import CouponStatus, CouponTemplate, DiscountType, RedemptionsLedger, UserCoupon
from app.models.merchant import KycStatus, Merchant, MerchantStaff, Sector
from app.models.reel import AudioType, Reel, ReelStatus
from app.models.user import User, UserRole
from tests.feature_helpers import (
    bearer,
    prepare_schema,
    reel_payload,
    seed_store,
    seed_user,
    unique_phone,
)


@pytest_asyncio.fixture(autouse=True)
async def init_db():
    await prepare_schema()
    yield


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_cashier_analytics_and_unique_customers(client: AsyncClient):
    """Cashier token on GET /merchants/analytics returns only that staff member's redemptions,
    and unique_customers counts distinct shoppers. Owner token returns store total."""
    store = await seed_store(with_staff=True)

    shopper1_id, _ = await seed_user("SHOPPER", "Shopper One")
    shopper2_id, _ = await seed_user("SHOPPER", "Shopper Two")

    async with async_session_factory() as session:
        # Create reel first (needed by CouponTemplate foreign key)
        reel = Reel(
            merchant_id=store.merchant_id,
            title="Analytics Test Reel",
            video_url="http://vid.com",
            thumbnail_url="http://thumb.com",
            duration_seconds=15,
            status=ReelStatus.APPROVED,
        )
        session.add(reel)
        await session.flush()

        # Create coupon template & user coupons
        tmpl = CouponTemplate(
            merchant_id=store.merchant_id,
            reel_id=reel.id,
            title="50 OFF",
            discount_type=DiscountType.FLAT_AMOUNT,
            discount_value=50,
            min_order_amount=200,
            validity_days=7,
        )
        session.add(tmpl)
        await session.flush()

        uc1 = UserCoupon(
            coupon_template_id=tmpl.id,
            user_id=shopper1_id,
            status=CouponStatus.REDEEMED,
            totp_secret="JBSWY3DPEHPK3PXP",
            expires_at=datetime.now(timezone.utc) + timedelta(days=5),
        )
        uc2 = UserCoupon(
            coupon_template_id=tmpl.id,
            user_id=shopper2_id,
            status=CouponStatus.REDEEMED,
            totp_secret="JBSWY3DPEHPK3PXP",
            expires_at=datetime.now(timezone.utc) + timedelta(days=5),
        )
        session.add_all([uc1, uc2])
        await session.flush()

        # Staff redeemed uc1 for shopper 1
        r1 = RedemptionsLedger(
            merchant_id=store.merchant_id,
            user_coupon_id=uc1.id,
            staff_id=store.staff_id,
            bill_amount=300,
            discount_applied=50,
        )
        # Owner redeemed uc2 for shopper 2 (staff_id=None)
        r2 = RedemptionsLedger(
            merchant_id=store.merchant_id,
            user_coupon_id=uc2.id,
            staff_id=None,
            bill_amount=500,
            discount_applied=50,
        )
        session.add_all([r1, r2])
        await session.commit()

    # Cashier calls analytics -> sees only staff_id == store.staff_id (1 redemption, 1 unique customer, 300 bill)
    resp = await client.get("/api/v1/merchants/analytics", headers=bearer(store.staff_token))
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["redemption_count"] == 1
    assert data["total_bill_amount"] == 300.0
    assert data["unique_customers"] == 1

    # Owner calls analytics -> sees store total (2 redemptions, 2 unique customers, 800 bill)
    owner_resp = await client.get("/api/v1/merchants/analytics", headers=bearer(store.owner_token))
    assert owner_resp.status_code == 200, owner_resp.text
    owner_data = owner_resp.json()["data"]
    assert owner_data["redemption_count"] == 2
    assert owner_data["total_bill_amount"] == 800.0
    assert owner_data["unique_customers"] == 2


@pytest.mark.asyncio
async def test_cashier_reels_mine_and_isolation(client: AsyncClient):
    """Cashier token on GET /reels/mine returns the store's reels; cashier of another store cannot see them."""
    store_a = await seed_store(with_staff=True)
    store_b = await seed_store(with_staff=True)

    async with async_session_factory() as session:
        reel_a = Reel(
            merchant_id=store_a.merchant_id,
            title="Store A Reel",
            video_url="http://vid.a",
            thumbnail_url="http://thumb.a",
            duration_seconds=15,
            status=ReelStatus.APPROVED,
        )
        reel_b = Reel(
            merchant_id=store_b.merchant_id,
            title="Store B Reel",
            video_url="http://vid.b",
            thumbnail_url="http://thumb.b",
            duration_seconds=15,
            status=ReelStatus.APPROVED,
        )
        session.add_all([reel_a, reel_b])
        await session.commit()

    # Cashier of store A sees store A's reel only
    resp = await client.get("/api/v1/reels/mine", headers=bearer(store_a.staff_token))
    assert resp.status_code == 200, resp.text
    items = resp.json()["data"]
    assert len(items) == 1
    assert items[0]["title"] == "Store A Reel"
    assert items[0]["is_verified"] is True  # Store A is APPROVED

    # Cashier of store B sees store B's reel only
    resp_b = await client.get("/api/v1/reels/mine", headers=bearer(store_b.staff_token))
    assert resp_b.status_code == 200, resp_b.text
    items_b = resp_b.json()["data"]
    assert len(items_b) == 1
    assert items_b[0]["title"] == "Store B Reel"


@pytest.mark.asyncio
async def test_cashier_write_route_rejection(client: AsyncClient):
    """A cashier token on POST /reels is still rejected (the write routes are untouched)."""
    store = await seed_store(with_staff=True, can_upload_reels=False)
    resp = await client.post("/api/v1/reels", json=reel_payload(), headers=bearer(store.staff_token))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_redemption_verify_and_pin_returns_customer_phone(client: AsyncClient):
    """verify and verify-pin responses include customer_phone."""
    store = await seed_store(with_staff=True)
    shopper_phone = unique_phone()

    async with async_session_factory() as session:
        user = User(phone=shopper_phone, full_name="Verified Shopper", role=UserRole.SHOPPER, is_active=True)
        session.add(user)
        await session.flush()

        reel = Reel(
            merchant_id=store.merchant_id,
            title="Redeem Reel",
            video_url="http://vid.com",
            thumbnail_url="http://thumb.com",
            duration_seconds=15,
            status=ReelStatus.APPROVED,
        )
        session.add(reel)
        await session.flush()

        tmpl = CouponTemplate(
            merchant_id=store.merchant_id,
            reel_id=reel.id,
            title="10% OFF",
            discount_type=DiscountType.PERCENTAGE,
            discount_value=10,
            min_order_amount=100,
            validity_days=5,
        )
        session.add(tmpl)
        await session.flush()

        totp_secret = "JBSWY3DPEHPK3PXP"
        import pyotp
        valid_pin = pyotp.TOTP(totp_secret, interval=60).now()

        coupon = UserCoupon(
            coupon_template_id=tmpl.id,
            user_id=user.id,
            status=CouponStatus.CLAIMED,
            totp_secret=totp_secret,
            expires_at=datetime.now(timezone.utc) + timedelta(days=5),
        )
        session.add(coupon)
        await session.commit()
        coupon_id = coupon.id

    # Test verify-pin
    pin_payload = {
        "user_coupon_id": str(coupon_id),
        "backup_pin": valid_pin,
        "bill_amount": 250.0,
    }
    resp = await client.post("/api/v1/redemptions/verify-pin", json=pin_payload, headers=bearer(store.staff_token))
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["customer_phone"] == shopper_phone


@pytest.mark.asyncio
async def test_is_verified_standard_and_public_store_relaxation(client: AsyncClient):
    """is_verified is true only for APPROVED stores on feed, store list, public profile, wallet;
    a PENDING store opens at GET /merchants/{id} with is_verified=false;
    a REJECTED store returns 404."""
    # Seed approved store
    approved_store = await seed_store()
    # Seed pending store
    owner_pending_id, _ = await seed_user("MERCHANT", "Pending Owner")
    # Seed rejected store
    owner_rejected_id, _ = await seed_user("MERCHANT", "Rejected Owner")

    async with async_session_factory() as session:
        m_pending = Merchant(
            user_id=owner_pending_id,
            business_name="Pending Store",
            sector=Sector.FOOD,
            address_text="Pending Address",
            city="Nagpur",
            latitude=21.1458,
            longitude=79.0882,
            kyc_doc_url="http://doc.pdf",
            kyc_status=KycStatus.PENDING,
        )
        m_rejected = Merchant(
            user_id=owner_rejected_id,
            business_name="Rejected Store",
            sector=Sector.FOOD,
            address_text="Rejected Address",
            city="Nagpur",
            latitude=21.1458,
            longitude=79.0882,
            kyc_doc_url="http://doc.pdf",
            kyc_status=KycStatus.REJECTED,
        )
        session.add_all([m_pending, m_rejected])
        await session.commit()
        pending_id = m_pending.id
        rejected_id = m_rejected.id

    # 1. Approved store public profile: returns 200, is_verified=True
    r_app = await client.get(f"/api/v1/merchants/{approved_store.merchant_id}")
    assert r_app.status_code == 200
    assert r_app.json()["data"]["is_verified"] is True

    # 2. Pending store public profile: returns 200 (relaxed per V3), is_verified=False
    r_pen = await client.get(f"/api/v1/merchants/{pending_id}")
    assert r_pen.status_code == 200
    assert r_pen.json()["data"]["is_verified"] is False

    # 3. Rejected store public profile: returns 404
    r_rej = await client.get(f"/api/v1/merchants/{rejected_id}")
    assert r_rej.status_code == 404

    # 4. Store list GET /merchants
    r_list = await client.get("/api/v1/merchants?city=Nagpur")
    assert r_list.status_code == 200
    shops = r_list.json()["data"]
    app_shop = next((s for s in shops if s["id"] == str(approved_store.merchant_id)), None)
    assert app_shop is not None
    assert app_shop["is_verified"] is True
    # Description should not say "Verified"
    assert "Verified" not in app_shop["description"]
