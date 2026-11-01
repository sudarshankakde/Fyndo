import pytest
import pytest_asyncio
from datetime import timedelta
from unittest.mock import patch

from app.core.time_utils import ist_now
from app.models.reel import Reel, ReelStatus
from app.services.cloudinary_service import CloudinaryService
from app.services.reel_lifecycle_service import sweep_reels
from tests.feature_helpers import prepare_schema, seed_store


@pytest_asyncio.fixture(autouse=True)
async def init_db():
    await prepare_schema()
    yield


def test_extract_cloudinary_public_id():
    # Standard URL with version and folder
    url1 = "https://res.cloudinary.com/fyndocloud/video/upload/v1710000000/fyndo/reels/video123.mp4"
    assert CloudinaryService.extract_public_id(url1) == "fyndo/reels/video123"

    # URL with transformation and version
    url2 = "https://res.cloudinary.com/fyndocloud/video/upload/f_auto,q_auto/v1/fyndo/reels/my_reel.mp4"
    assert CloudinaryService.extract_public_id(url2) == "fyndo/reels/my_reel"

    # Image thumbnail
    url3 = "https://res.cloudinary.com/fyndocloud/image/upload/v1234/fyndo/reels/thumb_xyz.webp"
    assert CloudinaryService.extract_public_id(url3) == "fyndo/reels/thumb_xyz"

    # URL with single transformation without comma (e.g. video poster start offset so_0)
    url_so = "https://res.cloudinary.com/fyndocloud/video/upload/so_0/v1234/fyndo/reels/thumb_so.jpg"
    assert CloudinaryService.extract_public_id(url_so) == "fyndo/reels/thumb_so"

    # URL with query parameters and hash
    url_query = "https://res.cloudinary.com/fyndocloud/video/upload/v1234/fyndo/reels/video.mp4?v=1.2.3#preview"
    assert CloudinaryService.extract_public_id(url_query) == "fyndo/reels/video"

    # Non-cloudinary or invalid URL
    assert CloudinaryService.extract_public_id("https://example.com/video.mp4") is None
    assert CloudinaryService.extract_public_id("/uploads/reels/video.mp4") is None
    assert CloudinaryService.extract_public_id(None) is None


@pytest.mark.asyncio
async def test_reel_assets_purged_only_after_grace_period():
    from app.core.database import async_session_factory

    store = await seed_store()
    now = ist_now()

    async with async_session_factory() as session:
        # Reel 1: within grace period (expired 5 hours ago, grace ends in 19 hours)
        reel_in_grace = Reel(
            merchant_id=store.merchant_id,
            title="In Grace Period",
            duration_seconds=15,
            video_url="https://res.cloudinary.com/demo/video/upload/v1/fyndo/reels/grace_video.mp4",
            thumbnail_url="https://res.cloudinary.com/demo/image/upload/v1/fyndo/reels/grace_thumb.jpg",
            status=ReelStatus.APPROVED,
            is_expired=True,
            expires_at=now - timedelta(hours=5),
            grace_period_until=now + timedelta(hours=19),
        )

        # Reel 2: past grace period (expired 30 hours ago, grace ended 6 hours ago)
        reel_past_grace = Reel(
            merchant_id=store.merchant_id,
            title="Past Grace Period",
            duration_seconds=15,
            video_url="https://res.cloudinary.com/demo/video/upload/v1/fyndo/reels/expired_video.mp4?v=1.0",
            thumbnail_url="https://res.cloudinary.com/demo/image/upload/so_0/v1/fyndo/reels/expired_thumb.jpg",
            cloudinary_public_id="fyndo/reels/expired_video_custom",
            status=ReelStatus.APPROVED,
            is_expired=True,
            expires_at=now - timedelta(hours=30),
            grace_period_until=now - timedelta(hours=6),
        )

        session.add_all([reel_in_grace, reel_past_grace])
        await session.commit()

    with patch.object(CloudinaryService, "destroy", return_value={"result": "ok"}) as mock_destroy:
        async with async_session_factory() as session:
            counts = await sweep_reels(session, now=now)
            await session.commit()

        # reel_past_grace should be removed, reel_in_grace should NOT be removed
        assert counts["removed"] == 1

        # destroy should have been called twice for reel_past_grace (video + thumb)
        assert mock_destroy.call_count == 2
        calls = mock_destroy.call_args_list

        destroyed_pids = [call.args[0] for call in calls]
        # Should prioritize reel.cloudinary_public_id when present
        assert "fyndo/reels/expired_video_custom" in destroyed_pids
        assert "fyndo/reels/expired_thumb" in destroyed_pids
        assert "fyndo/reels/grace_video" not in destroyed_pids


@pytest.mark.asyncio
async def test_delete_profile_video_purges_cloudinary():
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    from tests.feature_helpers import bearer

    store = await seed_store()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Set profile video first
        set_res = await client.patch(
            "/api/v1/merchants/me/profile-video",
            json={
                "profile_video_url": "https://res.cloudinary.com/demo/video/upload/v1/fyndo/showcase/intro_vid.mp4",
                "profile_video_thumbnail_url": "https://res.cloudinary.com/demo/image/upload/v1/fyndo/showcase/intro_thumb.jpg",
            },
            headers=bearer(store.owner_token),
        )
        assert set_res.status_code == 200

        with patch.object(CloudinaryService, "destroy", return_value={"result": "ok"}) as mock_destroy:
            del_res = await client.delete(
                "/api/v1/merchants/me/profile-video",
                headers=bearer(store.owner_token),
            )
            assert del_res.status_code == 200
            assert del_res.json()["data"]["profile_video_url"] is None
            assert mock_destroy.call_count == 2
            pids = [call.args[0] for call in mock_destroy.call_args_list]
            assert "fyndo/showcase/intro_vid" in pids
            assert "fyndo/showcase/intro_thumb" in pids
