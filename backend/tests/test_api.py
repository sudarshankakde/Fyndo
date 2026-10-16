import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest_asyncio.fixture(autouse=True)
async def init_db():
    from app.core.database import Base, engine
    import app.models  # ensure models registered
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest_asyncio.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
async def test_health_check(async_client: AsyncClient):
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["success"] is True
    assert json_data["data"]["status"] == "healthy"


@pytest.mark.asyncio
async def test_auth_otp_and_profile_flow(async_client: AsyncClient):
    phone = "+919876543210"

    # Step 1: Send OTP
    send_resp = await async_client.post(
        "/api/v1/auth/otp/send",
        json={"phone": phone, "channel": "SMS"}
    )
    assert send_resp.status_code == 200
    send_data = send_resp.json()
    assert send_data["success"] is True
    test_otp = send_data["data"]["test_otp"]
    assert test_otp is not None
    assert len(test_otp) == 6

    # Step 2: Verify OTP
    verify_resp = await async_client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": phone, "otp": test_otp, "preferred_language": "hi"}
    )
    assert verify_resp.status_code == 200
    verify_data = verify_resp.json()
    assert verify_data["success"] is True
    access_token = verify_data["data"]["access_token"]
    assert access_token is not None
    assert verify_data["data"]["user"]["phone"] == phone


@pytest.mark.asyncio
async def test_media_sign_upload(async_client: AsyncClient):
    # Authenticate user first
    phone = "+919876543211"
    send_resp = await async_client.post(
        "/api/v1/auth/otp/send",
        json={"phone": phone, "channel": "SMS"}
    )
    otp = send_resp.json()["data"]["test_otp"]
    verify_resp = await async_client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": phone, "otp": otp, "preferred_language": "en"}
    )
    token = verify_resp.json()["data"]["access_token"]

    # Request Cloudinary upload signature
    headers = {"Authorization": f"Bearer {token}"}
    sign_resp = await async_client.post(
        "/api/v1/media/sign-upload",
        json={"folder": "reels", "resource_type": "video"},
        headers=headers
    )
    assert sign_resp.status_code == 200
    sign_data = sign_resp.json()
    assert sign_data["success"] is True
    assert "signature" in sign_data["data"]
    assert "upload_url" in sign_data["data"]


@pytest.mark.asyncio
async def test_complete_merchant_and_redemption_vertical_slice(async_client: AsyncClient):
    import random
    suffix = random.randint(10000000, 99999999)
    owner_phone = f"+9198{suffix}"[:13]
    staff_phone = f"+9197{suffix}"[:13]
    s_resp = await async_client.post("/api/v1/auth/otp/send", json={"phone": owner_phone})
    v_resp = await async_client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": owner_phone, "otp": s_resp.json()["data"]["test_otp"], "preferred_language": "mr"}
    )
    owner_token = v_resp.json()["data"]["access_token"]
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    # Onboard store in Nagpur
    onboard_resp = await async_client.post(
        "/api/v1/merchants/onboard",
        json={
            "business_name": "Haldirams Sitabuldi",
            "sector": "FOOD",
            "address_text": "Main Road, Sitabuldi, Nagpur",
            "city": "Nagpur",
            "latitude": 21.1458,
            "longitude": 79.0882,
            "kyc_doc_url": "https://res.cloudinary.com/fyndo/image/upload/kyc_mock.pdf"
        },
        headers=owner_headers
    )
    assert onboard_resp.status_code == 200
    merchant_id = onboard_resp.json()["data"]["id"]

    # 2. Admin approves merchant KYC before reel publishing
    from app.core.config import settings
    master_admin_resp = await async_client.post(
        "/api/v1/auth/admin-login",
        json={
            "identifier": settings.SUPER_ADMIN_IDENTIFIER,
            "password": settings.SUPER_ADMIN_PASSWORD,
        },
    )
    assert master_admin_resp.status_code == 200
    master_admin_headers = {
        "Authorization": f"Bearer {master_admin_resp.json()['data']['access_token']}"
    }
    kyc_decision_resp = await async_client.post(
        f"/api/v1/admin/moderation/merchants/{merchant_id}/decision",
        json={"decision": "APPROVE"},
        headers=master_admin_headers,
    )
    assert kyc_decision_resp.status_code == 200

    # 3. Configure 1 Cashier Staff PIN
    staff_resp = await async_client.post(
        "/api/v1/merchants/staff",
        json={
            "staff_name": "Ramesh Cashier",
            "phone": staff_phone,
            "pin": "123456"
        },
        headers=owner_headers
    )
    assert staff_resp.status_code == 200

    # 4. Create Reel & Food Sector Coupon (Max 5 days)
    reel_resp = await async_client.post(
        "/api/v1/reels",
        json={
            "title": "Fresh Jalebi & Fafda 40% Off",
            "video_url": "https://res.cloudinary.com/fyndo/video/upload/jalebi.mp4",
            "thumbnail_url": "https://res.cloudinary.com/fyndo/image/upload/jalebi.webp",
            "duration_seconds": 30,
            "audio_type": "CAMERA_MIC",
            "coupon": {
                "title": "Flat 40% Off on Sweets",
                "discount_type": "PERCENTAGE",
                "discount_value": 40.0,
                "min_order_amount": 200.0,
                "validity_days": 3  # Food sector allows <= 5 days
            }
        },
        headers=owner_headers
    )
    assert reel_resp.status_code == 200
    reel_id = reel_resp.json()["data"]["reel_id"]

    reel_id = reel_resp.json()["data"]["reel_id"]

    # 5. Cashier Staff POS Login
    pos_login_resp = await async_client.post(
        "/api/v1/auth/staff-login",
        json={"store_phone": owner_phone, "pin": "123456"}
    )
    assert pos_login_resp.status_code == 200
    pos_token = pos_login_resp.json()["data"]["access_token"]
    pos_headers = {"Authorization": f"Bearer {pos_token}"}

    # 6. Admin Moderation: Setup Super Admin and approve reel
    import uuid
    from app.core.database import async_session_factory
    from app.models.user import User, UserRole

    admin_phone = f"+9199{suffix}"[:13]
    a_s_resp = await async_client.post("/api/v1/auth/otp/send", json={"phone": admin_phone})
    a_v_resp = await async_client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": admin_phone, "otp": a_s_resp.json()["data"]["test_otp"]}
    )
    admin_token = a_v_resp.json()["data"]["access_token"]
    admin_id = a_v_resp.json()["data"]["user"]["id"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    async with async_session_factory() as session:
        u = await session.get(User, uuid.UUID(admin_id))
        u.role = UserRole.SUPER_ADMIN
        await session.commit()

    # Admin lists pending reels
    pending_resp = await async_client.get("/api/v1/admin/moderation/reels", headers=admin_headers)
    assert pending_resp.status_code == 200
    assert any(item["id"] == reel_id for item in pending_resp.json()["data"])

    # Admin approves reel
    dec_resp = await async_client.post(
        f"/api/v1/admin/moderation/reels/{reel_id}/decision",
        json={"decision": "APPROVE"},
        headers=admin_headers
    )
    assert dec_resp.status_code == 200
    assert dec_resp.json()["data"]["status"] == "APPROVED"

    # 7. Shopper Discovery Feed: Approved reel is now discoverable!
    feed_resp = await async_client.get("/api/v1/reels/feed?lat=21.1460&lon=79.0880&radius_km=5&limit=50")
    assert feed_resp.status_code == 200
    feed_items = feed_resp.json()["data"]
    assert len(feed_items) >= 1
    matched_feed_reel = next(item for item in feed_items if item["id"] == reel_id)
    coupon_id = matched_feed_reel["coupon"]["id"]

    # 8. Shopper Claims Coupon to Wallet
    shopper_phone = f"+9196{suffix}"[:13]
    sh_s_resp = await async_client.post("/api/v1/auth/otp/send", json={"phone": shopper_phone})
    sh_v_resp = await async_client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": shopper_phone, "otp": sh_s_resp.json()["data"]["test_otp"]}
    )
    shopper_token = sh_v_resp.json()["data"]["access_token"]
    shopper_headers = {"Authorization": f"Bearer {shopper_token}"}

    claim_resp = await async_client.post(f"/api/v1/coupons/{coupon_id}/claim", headers=shopper_headers)
    assert claim_resp.status_code == 200
    user_coupon_id = claim_resp.json()["data"]["user_coupon_id"]

    # 9. Shopper Views Wallet
    wallet_resp = await async_client.get("/api/v1/coupons/wallet", headers=shopper_headers)
    assert wallet_resp.status_code == 200
    assert len(wallet_resp.json()["data"]) == 1
    assert wallet_resp.json()["data"][0]["status"] == "CLAIMED"

    # 10. Shopper Generates Dynamic TOTP QR
    qr_resp = await async_client.get(f"/api/v1/coupons/{user_coupon_id}/dynamic-qr", headers=shopper_headers)
    assert qr_resp.status_code == 200
    qr_payload = qr_resp.json()["data"]["qr_payload"]

    # 11. Cashier Terminal Verifies & Redeems Coupon
    redeem_resp = await async_client.post(
        "/api/v1/redemptions/verify",
        json={"qr_payload": qr_payload, "bill_amount": 500.0, "cashier_lat": 21.1458, "cashier_lon": 79.0882},
        headers=pos_headers
    )
    assert redeem_resp.status_code == 200
    assert redeem_resp.json()["data"]["status"] == "VERIFIED_AND_REDEEMED"

    # 12. Replay Prevention: Attempting to reuse same QR fails
    replay_resp = await async_client.post(
        "/api/v1/redemptions/verify",
        json={"qr_payload": qr_payload, "bill_amount": 500.0, "cashier_lat": 21.1458, "cashier_lon": 79.0882},
        headers=pos_headers
    )
    assert replay_resp.status_code == 409

    # 13. Wallet reflects REDEEMED
    wallet_resp2 = await async_client.get("/api/v1/coupons/wallet", headers=shopper_headers)
    assert wallet_resp2.status_code == 200
    assert wallet_resp2.json()["data"][0]["status"] == "REDEEMED"
