"""Verify non-logged-in / anonymous shopper view tracking."""
import uuid
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from tests.feature_helpers import (
    prepare_schema,
    seed_store,
)
from app.models.reel import Reel, ReelStatus
from app.core.database import async_session_factory
from app.services.reel_engagement_service import record_view


@pytest_asyncio.fixture(autouse=True)
async def init_db():
    await prepare_schema()


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_anonymous_view_tracking(client):
    store = await seed_store(sector="CAFE_COFFEE_SHOPS")
    merchant_id = store.merchant_id

    # Create live reel directly in DB
    reel_id = uuid.uuid4()
    async with async_session_factory() as session:
        reel = Reel(
            id=reel_id,
            merchant_id=merchant_id,
            title="Cold Brew Special",
            video_url="https://example.com/video.mp4",
            thumbnail_url="https://example.com/thumb.jpg",
            duration_seconds=30,
            status=ReelStatus.APPROVED,
            views_count=0,
        )
        session.add(reel)
        await session.commit()

    # 1. Anonymous viewer 1 records a view
    resp1 = await client.post(
        f"/api/v1/reels/{reel_id}/view",
        headers={"X-Viewer-ID": "browser-session-anon-1", "User-Agent": "TestBrowser/1.0"},
    )
    assert resp1.status_code == 200
    data1 = resp1.json()["data"]
    assert data1["views_count"] == 1
    assert data1["counted"] is True

    # 2. Same anonymous viewer sends repeat view (deduped within same day)
    resp2 = await client.post(
        f"/api/v1/reels/{reel_id}/view",
        headers={"X-Viewer-ID": "browser-session-anon-1", "User-Agent": "TestBrowser/1.0"},
    )
    assert resp2.status_code == 200
    data2 = resp2.json()["data"]
    assert data2["counted"] is False

    # 3. Different anonymous viewer (e.g. mobile device) records view
    resp3 = await client.post(
        f"/api/v1/reels/{reel_id}/view",
        headers={"X-Device-ID": "mobile-device-anon-2", "User-Agent": "MobileApp/2.0"},
    )
    assert resp3.status_code == 200
    data3 = resp3.json()["data"]
    assert data3["views_count"] == 2
    assert data3["counted"] is True
