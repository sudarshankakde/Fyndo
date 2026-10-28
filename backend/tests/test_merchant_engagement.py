"""Client requirements 2, 3, 4, 11: profile video, call tracking, follows, ratings."""
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from tests.feature_helpers import bearer, prepare_schema, seed_store, seed_user


@pytest_asyncio.fixture(autouse=True)
async def init_db():
    await prepare_schema()
    yield


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_profile_video_is_saved_and_public(client):
    store = await seed_store()
    resp = await client.patch(
        "/api/v1/merchants/me/profile-video",
        json={
            "profile_video_url": "https://res.cloudinary.com/fyndo/video/upload/store.mp4",
            "profile_video_thumbnail_url": "https://res.cloudinary.com/fyndo/image/upload/store.webp",
        },
        headers=bearer(store.owner_token),
    )
    assert resp.status_code == 200, resp.text

    public = (await client.get(f"/api/v1/merchants/{store.merchant_id}")).json()["data"]
    assert public["profile_video_url"].endswith("store.mp4")
    assert public["profile_video_thumbnail_url"].endswith("store.webp")

    own = (await client.get("/api/v1/merchants/profile", headers=bearer(store.owner_token))).json()
    assert own["data"]["profile_video_url"].endswith("store.mp4")


@pytest.mark.asyncio
async def test_profile_video_requires_store_owner(client):
    _, shopper_token = await seed_user()
    resp = await client.patch(
        "/api/v1/merchants/me/profile-video",
        json={"profile_video_url": "https://example.com/v.mp4"},
        headers=bearer(shopper_token),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_call_clicks_are_tracked_and_deduplicated(client):
    store = await seed_store()
    _, shopper_token = await seed_user()
    url = f"/api/v1/merchants/{store.merchant_id}/track-call"

    first = await client.post(url, headers=bearer(shopper_token))
    repeat = await client.post(url, headers=bearer(shopper_token))
    anonymous = await client.post(url, json={"device_fingerprint": "device-abc"})
    assert first.json()["data"]["counted"] is True
    assert repeat.json()["data"]["counted"] is False
    assert anonymous.json()["data"]["counted"] is True

    insights = await client.get("/api/v1/merchants/me/insights", headers=bearer(store.owner_token))
    assert insights.status_code == 200
    assert insights.json()["data"]["call_clicks_total"] == 2
    assert insights.json()["data"]["call_clicks_last_7_days"] == 2


@pytest.mark.asyncio
async def test_follow_toggle_and_following_list(client):
    store = await seed_store()
    _, shopper_token = await seed_user()
    url = f"/api/v1/merchants/{store.merchant_id}/follow"

    followed = (await client.post(url, headers=bearer(shopper_token))).json()["data"]
    assert followed == {
        "merchant_id": str(store.merchant_id), "is_following": True, "followers_count": 1
    }

    following = await client.get("/api/v1/merchants/following", headers=bearer(shopper_token))
    assert following.status_code == 200
    assert [m["id"] for m in following.json()["data"]] == [str(store.merchant_id)]

    public = (
        await client.get(f"/api/v1/merchants/{store.merchant_id}", headers=bearer(shopper_token))
    ).json()["data"]
    assert public["is_following"] is True and public["followers_count"] == 1

    unfollowed = (await client.post(url, headers=bearer(shopper_token))).json()["data"]
    assert unfollowed["is_following"] is False and unfollowed["followers_count"] == 0


@pytest.mark.asyncio
async def test_owner_cannot_follow_or_rate_own_store(client):
    store = await seed_store()
    follow = await client.post(
        f"/api/v1/merchants/{store.merchant_id}/follow", headers=bearer(store.owner_token)
    )
    rate = await client.post(
        f"/api/v1/merchants/{store.merchant_id}/rate",
        json={"rating": 5},
        headers=bearer(store.owner_token),
    )
    assert follow.status_code == 400
    assert rate.status_code == 400


@pytest.mark.asyncio
async def test_ratings_validate_upsert_and_aggregate(client):
    store = await seed_store()
    _, alice = await seed_user(full_name="Alice")
    _, bob = await seed_user(full_name="Bob")
    url = f"/api/v1/merchants/{store.merchant_id}/rate"

    invalid = await client.post(url, json={"rating": 6}, headers=bearer(alice))
    assert invalid.status_code == 422

    await client.post(url, json={"rating": 2}, headers=bearer(alice))
    await client.post(url, json={"rating": 4, "review_text": "Great samosas"}, headers=bearer(alice))
    await client.post(url, json={"rating": 5}, headers=bearer(bob))

    summary = (
        await client.get(f"/api/v1/merchants/{store.merchant_id}/ratings", headers=bearer(alice))
    ).json()["data"]
    assert summary["count"] == 2
    assert summary["average"] == 4.5
    assert summary["breakdown"]["4"] == 1 and summary["breakdown"]["5"] == 1
    assert summary["my_rating"] == 4
    assert {r["user_name"] for r in summary["reviews"]} == {"Alice", "Bob"}

    public = (await client.get(f"/api/v1/merchants/{store.merchant_id}")).json()["data"]
    assert public["rating_average"] == 4.5 and public["rating_count"] == 2


@pytest.mark.asyncio
async def test_public_merchant_contact_and_about_fields(client):
    store = await seed_store()

    # Check default (no store phone set yet) -> falls back to owner's phone
    public1 = (await client.get(f"/api/v1/merchants/{store.merchant_id}")).json()["data"]
    assert public1["phone"] is not None and public1["phone"].startswith("+91")

    # Update profile with custom phone, description, and business_hours
    update_res = await client.patch(
        "/api/v1/merchants/profile",
        json={
            "phone": "+91 99999 88888",
            "description": "Authentic sourdough bakery",
            "business_hours": "Mon-Sat 9am-9pm",
            "website": "https://bakery.example.com",
            "sub_categories": ["Bakery", "Artisan"],
        },
        headers=bearer(store.owner_token),
    )
    assert update_res.status_code == 200

    public2 = (await client.get(f"/api/v1/merchants/{store.merchant_id}")).json()["data"]
    assert public2["phone"] == "+91 99999 88888"
    assert public2["description"] == "Authentic sourdough bakery"
    assert public2["business_hours"] == "Mon-Sat 9am-9pm"
    assert public2["website"] == "https://bakery.example.com"
    assert public2["sub_categories"] == ["Bakery", "Artisan"]
