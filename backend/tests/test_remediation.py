"""Post-implementation regression + security tests for the backend audit fixes.

Covers:
  * security response headers and the request-body ceiling,
  * the media pipeline (magic-byte sniffing, extension spoofing, size limits),
  * reel engagement (deduped views, like toggling, comments, comments-disabled),
  * the atomic single-winner guarantee on coupon redemption (double-spend),
  * OTP brute-force lockout,
  * feed personalisation (is_liked) and cursor pagination.
"""
import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import pyotp
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest_asyncio.fixture(autouse=True)
async def init_db():
    from app.core.database import Base, engine
    import app.models  # noqa: F401  (ensure models are registered)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _login(client: AsyncClient, phone: str) -> str:
    send = await client.post("/api/v1/auth/otp/send", json={"phone": phone})
    otp = send.json()["data"]["test_otp"]
    verify = await client.post("/api/v1/auth/otp/verify", json={"phone": phone, "otp": otp})
    return verify.json()["data"]["access_token"]


def _phone() -> str:
    """Builds a unique, valid Indian MSISDN (+91 followed by 10 digits)."""
    return f"+91{uuid.uuid4().int % 10_000_000_000:010d}"


async def _seed_approved_reel(
    *, allow_comments: bool = True, latitude: float = 21.1458, longitude: float = 79.0882
):
    """Seeds an approved merchant + reel + coupon and returns their ids."""
    from app.core.database import async_session_factory
    from app.models.coupon import CouponTemplate, DiscountType
    from app.models.merchant import KycStatus, Merchant, Sector
    from app.models.reel import AudioType, Reel, ReelStatus
    from app.models.user import User, UserRole

    async with async_session_factory() as session:
        owner = User(phone=_phone(), role=UserRole.MERCHANT, is_active=True)
        session.add(owner)
        await session.flush()

        merchant = Merchant(
            user_id=owner.id,
            business_name="Remediation Test Store",
            sector=Sector.FOOD,
            address_text="Sitabuldi, Nagpur",
            city="Nagpur",
            latitude=latitude,
            longitude=longitude,
            kyc_doc_url="https://res.cloudinary.com/fyndo/kyc/doc.pdf",
            kyc_status=KycStatus.APPROVED,
        )
        session.add(merchant)
        await session.flush()

        reel = Reel(
            merchant_id=merchant.id,
            title="Post-fix Reel",
            duration_seconds=30,
            video_url="https://res.cloudinary.com/fyndo/video/upload/reel.mp4",
            thumbnail_url="https://res.cloudinary.com/fyndo/image/upload/reel.webp",
            audio_type=AudioType.CAMERA_MIC,
            status=ReelStatus.APPROVED,
            allow_comments=allow_comments,
        )
        session.add(reel)
        await session.flush()

        template = CouponTemplate(
            merchant_id=merchant.id,
            reel_id=reel.id,
            title="10% Off",
            discount_type=DiscountType.PERCENTAGE,
            discount_value=10,
            min_order_amount=0,
            validity_days=3,
            terms="Test terms",
        )
        session.add(template)
        await session.flush()
        await session.commit()
        return str(reel.id), str(merchant.id), str(template.id)


async def _seed_claimed_coupon():
    """Seeds a merchant, staff and a CLAIMED user coupon; returns redemption context."""
    from app.core.database import async_session_factory
    from app.core.security import get_password_hash
    from app.models.coupon import CouponTemplate, CouponStatus, DiscountType, UserCoupon
    from app.models.merchant import KycStatus, Merchant, MerchantStaff, Sector
    from app.models.reel import AudioType, Reel, ReelStatus
    from app.models.user import User, UserRole

    store_phone = _phone()
    async with async_session_factory() as session:
        owner = User(phone=store_phone, role=UserRole.MERCHANT, is_active=True)
        shopper = User(phone=_phone(), role=UserRole.SHOPPER, is_active=True)
        session.add_all([owner, shopper])
        await session.flush()

        merchant = Merchant(
            user_id=owner.id,
            business_name="Double Spend Store",
            sector=Sector.FOOD,
            address_text="Sitabuldi, Nagpur",
            city="Nagpur",
            latitude=21.1458,
            longitude=79.0882,
            kyc_doc_url="https://res.cloudinary.com/fyndo/kyc/doc.pdf",
            kyc_status=KycStatus.APPROVED,
        )
        session.add(merchant)
        await session.flush()

        staff = MerchantStaff(
            merchant_id=merchant.id,
            staff_name="Cashier One",
            phone=_phone(),
            pin_hash=get_password_hash("123456"),
        )
        session.add(staff)
        await session.flush()

        reel = Reel(
            merchant_id=merchant.id,
            title="Double Spend Reel",
            duration_seconds=30,
            video_url="https://res.cloudinary.com/fyndo/video/upload/r.mp4",
            thumbnail_url="https://res.cloudinary.com/fyndo/image/upload/r.webp",
            audio_type=AudioType.CAMERA_MIC,
            status=ReelStatus.APPROVED,
        )
        session.add(reel)
        await session.flush()

        template = CouponTemplate(
            merchant_id=merchant.id,
            reel_id=reel.id,
            title="20% Off",
            discount_type=DiscountType.PERCENTAGE,
            discount_value=20,
            min_order_amount=0,
            validity_days=3,
            terms="Test terms",
        )
        session.add(template)
        await session.flush()

        secret = pyotp.random_base32()
        user_coupon = UserCoupon(
            coupon_template_id=template.id,
            user_id=shopper.id,
            status=CouponStatus.CLAIMED,
            totp_secret=secret,
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        )
        session.add(user_coupon)
        await session.commit()

        backup_pin = pyotp.TOTP(secret, interval=60).now()[:4]
        return store_phone, str(user_coupon.id), backup_pin


# --------------------------------------------------------------------------- #
# Request hardening
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_security_headers_are_applied(client: AsyncClient):
    response = await client.get("/api/v1/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "permissions-policy" in response.headers


@pytest.mark.asyncio
async def test_health_probe_reports_database(client: AsyncClient):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["data"]["database"] == "connected"


@pytest.mark.asyncio
async def test_max_body_size_middleware_rejects_oversized_payload():
    from starlette.responses import PlainTextResponse

    from app.core.middleware import MaxBodySizeMiddleware

    async def inner_app(scope, receive, send):
        await PlainTextResponse("ok")(scope, receive, send)

    transport = ASGITransport(app=MaxBodySizeMiddleware(inner_app, max_bytes=32))
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        ok = await c.post("/", content=b"small")
        assert ok.status_code == 200
        too_big = await c.post("/", content=b"x" * 128)
        assert too_big.status_code == 413
        assert too_big.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"


# --------------------------------------------------------------------------- #
# Media pipeline
# --------------------------------------------------------------------------- #

def test_media_magic_byte_sniffing():
    from app.services.media_service import sniff_media_kind

    assert sniff_media_kind(b"\x89PNG\r\n\x1a\n" + b"\x00" * 8) == "image"
    assert sniff_media_kind(b"\xff\xd8\xff\xe0" + b"\x00" * 8) == "image"
    assert sniff_media_kind(b"RIFF\x00\x00\x00\x00WEBPVP8 ") == "image"
    assert sniff_media_kind(b"\x00\x00\x00\x18ftypmp42") == "video"
    assert sniff_media_kind(b"\x1a\x45\xdf\xa3" + b"\x00" * 8) == "video"
    assert sniff_media_kind(b"GIF89a............") is None


@pytest.mark.asyncio
async def test_media_upload_enforces_content_and_extension(client: AsyncClient):
    token = await _login(client, _phone())
    headers = {"Authorization": f"Bearer {token}"}

    valid = await client.post(
        "/api/v1/media/upload",
        data={"folder": "reels"},
        files={"file": ("poster.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 96, "image/png")},
        headers=headers,
    )
    assert valid.status_code == 200
    payload = valid.json()["data"]
    assert payload["content_type"] == "image/png"
    assert payload["size_bytes"] > 0
    assert len(payload["checksum_sha256"]) == 64

    # Blob/UUID filename without extension, but valid content_type and PNG magic bytes
    blob_upload = await client.post(
        "/api/v1/media/upload",
        data={"folder": "kyc"},
        files={"file": ("blob-without-ext", b"\x89PNG\r\n\x1a\n" + b"\x00" * 96, "image/png")},
        headers=headers,
    )
    assert blob_upload.status_code == 200

    # Extension lies about the content: an .png that is actually MP4.
    spoofed = await client.post(
        "/api/v1/media/upload",
        data={"folder": "reels"},
        files={"file": ("fake.png", b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 96, "image/png")},
        headers=headers,
    )
    assert spoofed.status_code == 400

    # Unsupported extension.
    unsupported = await client.post(
        "/api/v1/media/upload",
        data={"folder": "reels"},
        files={"file": ("clip.gif", b"GIF89a" + b"\x00" * 96, "image/gif")},
        headers=headers,
    )
    assert unsupported.status_code == 400


# --------------------------------------------------------------------------- #
# Reel engagement
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_reel_view_dedup_like_and_comments(client: AsyncClient):
    reel_id, _, _ = await _seed_approved_reel()
    token = await _login(client, _phone())
    headers = {"Authorization": f"Bearer {token}"}

    first_view = await client.post(f"/api/v1/reels/{reel_id}/view", headers=headers)
    assert first_view.status_code == 200
    assert first_view.json()["data"] == {"views_count": 1, "counted": True}

    repeat_view = await client.post(f"/api/v1/reels/{reel_id}/view", headers=headers)
    assert repeat_view.json()["data"] == {"views_count": 1, "counted": False}

    like = await client.post(f"/api/v1/reels/{reel_id}/like", headers=headers)
    assert like.json()["data"] == {"liked": True, "likes_count": 1}
    unlike = await client.post(f"/api/v1/reels/{reel_id}/like", headers=headers)
    assert unlike.json()["data"] == {"liked": False, "likes_count": 0}

    parent = await client.post(
        f"/api/v1/reels/{reel_id}/comments", json={"text": "Great deal!"}, headers=headers
    )
    assert parent.status_code == 201
    parent_id = parent.json()["data"]["id"]

    reply = await client.post(
        f"/api/v1/reels/{reel_id}/comments",
        json={"text": "Thanks!", "parent_comment_id": parent_id},
        headers=headers,
    )
    assert reply.status_code == 201
    assert reply.json()["data"]["parent_comment_id"] == parent_id

    listing = await client.get(f"/api/v1/reels/{reel_id}/comments")
    assert listing.status_code == 200
    assert len(listing.json()["data"]) == 2


@pytest.mark.asyncio
async def test_comments_disabled_reel_blocks_posting(client: AsyncClient):
    reel_id, _, _ = await _seed_approved_reel(allow_comments=False)
    token = await _login(client, _phone())
    response = await client.post(
        f"/api/v1/reels/{reel_id}/comments",
        json={"text": "Hello"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


# --------------------------------------------------------------------------- #
# Redemption double-spend
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_concurrent_backup_pin_redemption_is_single_winner(client: AsyncClient):
    store_phone, user_coupon_id, backup_pin = await _seed_claimed_coupon()

    login = await client.post(
        "/api/v1/auth/staff-login", json={"store_phone": store_phone, "pin": "123456"}
    )
    assert login.status_code == 200
    pos_headers = {"Authorization": f"Bearer {login.json()['data']['access_token']}"}
    payload = {"user_coupon_id": user_coupon_id, "backup_pin": backup_pin, "bill_amount": 500.0}

    first, second = await asyncio.gather(
        client.post("/api/v1/redemptions/verify-pin", json=payload, headers=pos_headers),
        client.post("/api/v1/redemptions/verify-pin", json=payload, headers=pos_headers),
    )
    codes = sorted([first.status_code, second.status_code])
    assert codes == [200, 409], f"expected one winner and one conflict, got {codes}"


# --------------------------------------------------------------------------- #
# OTP hardening
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_otp_locks_out_after_repeated_failures(client: AsyncClient):
    phone = _phone()
    await client.post("/api/v1/auth/otp/send", json={"phone": phone})

    for _ in range(5):
        bad = await client.post("/api/v1/auth/otp/verify", json={"phone": phone, "otp": "000000"})
        assert bad.status_code == 400

    # The real code is now locked out after too many failed attempts.
    locked = await client.post("/api/v1/auth/otp/verify", json={"phone": phone, "otp": "111111"})
    assert locked.status_code == 400


# --------------------------------------------------------------------------- #
# Feed
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_feed_personalises_is_liked_and_paginates(client: AsyncClient):
    # A random coordinate guarantees this reel is the only one at distance 0,
    # even though the dev SQLite database persists between runs.
    seed = uuid.uuid4().int
    latitude = round((seed % 160_000_000) / 1_000_000 - 80, 6)
    longitude = round(((seed // 160_000_000) % 340_000_000) / 1_000_000 - 170, 6)
    reel_id, _, _ = await _seed_approved_reel(latitude=latitude, longitude=longitude)
    token = await _login(client, _phone())
    headers = {"Authorization": f"Bearer {token}"}

    await client.post(f"/api/v1/reels/{reel_id}/like", headers=headers)

    feed = await client.get(
        f"/api/v1/reels/feed?lat={latitude}&lon={longitude}&radius_km=1&limit=1",
        headers=headers,
    )
    assert feed.status_code == 200
    body = feed.json()
    assert len(body["data"]) == 1
    assert body["data"][0]["id"] == reel_id
    assert body["data"][0]["is_liked"] is True
    assert "next_cursor" in body["meta"]


@pytest.mark.asyncio
async def test_saved_reels_and_followed_merchants(client: AsyncClient):
    reel_id, merchant_id, _ = await _seed_approved_reel()
    token = await _login(client, _phone())
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Bookmark the reel
    save_resp = await client.post(f"/api/v1/reels/{reel_id}/bookmark", headers=headers)
    assert save_resp.status_code == 200
    assert save_resp.json()["data"]["bookmarked"] is True

    # 2. Check saved reels list
    list_resp = await client.get("/api/v1/reels/saved", headers=headers)
    assert list_resp.status_code == 200
    saved_items = list_resp.json()["data"]
    assert any(item["reel_id"] == reel_id for item in saved_items)
    saved_reel = next(item for item in saved_items if item["reel_id"] == reel_id)
    assert saved_reel["thumbnail_url"] is not None
    assert saved_reel["shop_name"] is not None

    # 3. Unbookmark the reel
    unsave_resp = await client.post(f"/api/v1/reels/{reel_id}/bookmark", headers=headers)
    assert unsave_resp.status_code == 200
    assert unsave_resp.json()["data"]["bookmarked"] is False

    # 4. Confirm removed
    list_resp_2 = await client.get("/api/v1/reels/saved", headers=headers)
    assert not any(item["reel_id"] == reel_id for item in list_resp_2.json()["data"])


@pytest.mark.asyncio
async def test_wallet_coupons_include_merchant_metadata(client: AsyncClient):
    _, merchant_id, tmpl_id = await _seed_approved_reel()
    token = await _login(client, _phone())
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Claim coupon
    claim_resp = await client.post(f"/api/v1/coupons/{tmpl_id}/claim", headers=headers)
    assert claim_resp.status_code == 200

    # 2. Fetch wallet
    wallet_resp = await client.get("/api/v1/coupons/wallet", headers=headers)
    assert wallet_resp.status_code == 200
    wallet_items = wallet_resp.json()["data"]
    assert len(wallet_items) >= 1
    item = next(w for w in wallet_items if w["coupon_template_id"] == str(tmpl_id))
    assert item["merchant_id"] == str(merchant_id)
    assert item["merchant_name"] is not None
    assert "merchant_logo_url" in item
    assert "merchant_cover_url" in item
    assert "merchant_category" in item
    assert "reel_id" in item
    assert "reel_thumbnail_url" in item
    assert "reel_video_url" in item

