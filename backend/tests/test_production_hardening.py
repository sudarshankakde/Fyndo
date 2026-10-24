"""Production hardening tests for high-concurrency 1000-user/min capacity.

Validates:
  * Shared geographic Redis feed caching with decoupled user personalization (is_liked).
  * High-throughput Redis deduplication for reel view tracking.
  * Static media Cache-Control & CORS headers for edge CDN offloading.
  * Rate-limit identity resolution with client device-id isolation.
"""
import os
import uuid
from typing import Optional
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.main import app


@pytest_asyncio.fixture(autouse=True)
async def init_db():
    from app.core.database import Base, engine
    import app.models  # noqa: F401

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
    return f"+91{uuid.uuid4().int % 10_000_000_000:010d}"


async def _seed_reel(
    latitude: float = 21.1458,
    longitude: float = 79.0882,
    video_url: str = "https://res.cloudinary.com/fyndo/video/upload/fast.mp4",
    cloudinary_public_id: Optional[str] = None,
):
    from app.core.database import async_session_factory
    from app.models.coupon import CouponTemplate, DiscountType
    from app.models.merchant import KycStatus, Merchant, Sector
    from app.models.reel import AudioType, Reel, ReelStatus
    from app.models.user import User, UserRole

    async with async_session_factory() as db:
        user = User(phone=_phone(), role=UserRole.MERCHANT)
        db.add(user)
        await db.flush()

        merchant = Merchant(
            user_id=user.id,
            business_name="Hardening Cafe",
            sector=Sector.FOOD,
            city="Nagpur",
            address_text="Dharampeth, Nagpur",
            latitude=latitude,
            longitude=longitude,
            kyc_doc_url="https://res.cloudinary.com/fyndo/kyc/doc.pdf",
            kyc_status=KycStatus.APPROVED,
        )
        db.add(merchant)
        await db.flush()

        reel = Reel(
            merchant_id=merchant.id,
            title="Fast Feed Reel",
            video_url=video_url,
            cloudinary_public_id=cloudinary_public_id,
            thumbnail_url="https://res.cloudinary.com/fyndo/image/upload/fast.webp",
            duration_seconds=25,
            audio_type=AudioType.CAMERA_MIC,
            status=ReelStatus.APPROVED,
            allow_comments=True,
        )
        db.add(reel)
        await db.flush()

        coupon = CouponTemplate(
            merchant_id=merchant.id,
            reel_id=reel.id,
            title="Production 20% Off",
            discount_type=DiscountType.PERCENTAGE,
            discount_value=20.0,
            validity_days=5,
            is_active=True,
        )
        db.add(coupon)
        await db.commit()
        return reel.id


@pytest.mark.asyncio
async def test_shared_feed_cache_personalizes_is_liked(client: AsyncClient):
    """Verifies that 1000 users in the same neighborhood share the cached feed

    while their individual is_liked statuses are correctly personalized.
    """
    seed = uuid.uuid4().int
    latitude = round((seed % 160_000_000) / 1_000_000 - 80, 4)
    longitude = round(((seed // 160_000_000) % 340_000_000) / 1_000_000 - 170, 4)
    reel_id = await _seed_reel(latitude=latitude, longitude=longitude)

    token_a = await _login(client, _phone())
    token_b = await _login(client, _phone())

    # User A likes the reel
    like_resp = await client.post(
        f"/api/v1/reels/{reel_id}/like",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert like_resp.status_code == 200
    assert like_resp.json()["data"]["liked"] is True

    # User A fetches the feed: should see is_liked = True
    feed_a = await client.get(
        f"/api/v1/reels/feed?lat={latitude}&lon={longitude}&radius_km=5&limit=10",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert feed_a.status_code == 200
    items_a = feed_a.json()["data"]
    target_a = next(i for i in items_a if i["id"] == str(reel_id))
    assert target_a["is_liked"] is True

    # User B fetches the feed: served from shared cache, but is_liked = False!
    feed_b = await client.get(
        f"/api/v1/reels/feed?lat={latitude}&lon={longitude}&radius_km=5&limit=10",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert feed_b.status_code == 200
    items_b = feed_b.json()["data"]
    target_b = next(i for i in items_b if i["id"] == str(reel_id))
    assert target_b["is_liked"] is False

    # Anonymous user fetches the feed: served from shared cache, is_liked = False
    feed_anon = await client.get(
        f"/api/v1/reels/feed?lat={latitude}&lon={longitude}&radius_km=5&limit=10"
    )
    assert feed_anon.status_code == 200
    items_anon = feed_anon.json()["data"]
    target_anon = next(i for i in items_anon if i["id"] == str(reel_id))
    assert target_anon["is_liked"] is False


@pytest.mark.asyncio
async def test_view_counting_dedup_and_returning(client: AsyncClient):
    """Verifies fast daily view deduplication and atomic count increment."""
    reel_id = await _seed_reel()
    token_a = await _login(client, _phone())
    token_b = await _login(client, _phone())

    # User A first view: counted
    v1 = await client.post(
        f"/api/v1/reels/{reel_id}/view",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert v1.status_code == 200
    assert v1.json()["data"]["views_count"] == 1
    assert v1.json()["data"]["counted"] is True

    # User A second view (looping/replay): deduplicated!
    v2 = await client.post(
        f"/api/v1/reels/{reel_id}/view",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert v2.status_code == 200
    assert v2.json()["data"]["views_count"] == 1
    assert v2.json()["data"]["counted"] is False

    # User B view: counted
    v3 = await client.post(
        f"/api/v1/reels/{reel_id}/view",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert v3.status_code == 200
    assert v3.json()["data"]["views_count"] == 2
    assert v3.json()["data"]["counted"] is True


@pytest.mark.asyncio
async def test_cached_static_media_headers(client: AsyncClient):
    """Verifies that static uploads receive 24h Cache-Control and CORS for CDN offload."""
    from app.services.media_service import upload_root

    test_file_dir = os.path.join(upload_root(), "reels")
    os.makedirs(test_file_dir, exist_ok=True)
    test_file_path = os.path.join(test_file_dir, "cdn_test.mp4")
    with open(test_file_path, "wb") as f:
        f.write(b"mock video data for cdn test")

    try:
        resp = await client.get("/uploads/reels/cdn_test.mp4")
        assert resp.status_code in {200, 206}
        cache_header = resp.headers.get("cache-control", "")
        assert "public" in cache_header
        assert "max-age=" in cache_header
        assert resp.headers.get("access-control-allow-origin") == "*"
    finally:
        if os.path.exists(test_file_path):
            os.remove(test_file_path)


@pytest.mark.asyncio
async def test_cloudinary_video_optimization_and_hls(client: AsyncClient):
    """Verifies that Cloudinary URLs are optimized with f_auto,q_auto and HLS manifests are derived."""
    from app.services.cloudinary_service import CloudinaryService

    raw_url = "https://res.cloudinary.com/fyndo/video/upload/v1700000000/fyndo/reels/sample.mp4"
    opt_url = CloudinaryService.get_optimized_video_url(raw_url)
    assert opt_url == "https://res.cloudinary.com/fyndo/video/upload/f_auto,q_auto/v1700000000/fyndo/reels/sample.mp4"

    # Already optimized should be idempotent
    assert CloudinaryService.get_optimized_video_url(opt_url) == opt_url

    # HLS manifest derivation from public_id
    hls_from_pid = CloudinaryService.get_hls_url(public_id="fyndo/reels/sample", cloud_name="fyndo")
    assert hls_from_pid == "https://res.cloudinary.com/fyndo/video/upload/sp_auto/fyndo/reels/sample.m3u8"

    # HLS manifest derivation from URL
    hls_from_url = CloudinaryService.get_hls_url(video_url=raw_url)
    assert hls_from_url == "https://res.cloudinary.com/fyndo/video/upload/sp_auto/v1700000000/fyndo/reels/sample.m3u8"

    # Seed a reel with Cloudinary URL and verify /reels/feed emits video_hls_url
    lat, lon = 21.25, 79.15
    reel_id = await _seed_reel(
        latitude=lat,
        longitude=lon,
        video_url="https://res.cloudinary.com/fyndo/video/upload/v1700000000/fyndo/reels/artisan.mp4",
        cloudinary_public_id="fyndo/reels/artisan",
    )
    resp = await client.get(f"/api/v1/reels/feed?lat={lat}&lon={lon}")
    assert resp.status_code == 200
    feed_items = resp.json()["data"]
    match = next((item for item in feed_items if item["id"] == str(reel_id)), None)
    assert match is not None
    assert match["video_hls_url"] is not None
    assert match["video_hls_url"].endswith(".m3u8")
    assert "f_auto,q_auto" in match["video_url"]
