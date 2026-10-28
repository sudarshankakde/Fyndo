"""Client requirements 6, 7, 8, 10, 12: cashier uploads, auto-approve, offer expiry."""
import uuid
from datetime import timedelta

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from tests.feature_helpers import (
    bearer,
    prepare_schema,
    reel_payload,
    seed_store,
    seed_user,
    set_auto_approve,
)


@pytest_asyncio.fixture(autouse=True)
async def init_db():
    await prepare_schema()
    await set_auto_approve(False)
    yield
    await set_auto_approve(False)


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def _load_reel(reel_id: str):
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.core.database import async_session_factory
    from app.models.reel import Reel

    async with async_session_factory() as session:
        return (
            await session.execute(
                select(Reel).options(selectinload(Reel.coupon_template)).where(Reel.id == uuid.UUID(reel_id))
            )
        ).scalars().first()


async def _sweep_at(offset: timedelta):
    from app.core.database import async_session_factory
    from app.services.reel_lifecycle_service import sweep_reels, utcnow

    async with async_session_factory() as session:
        counts = await sweep_reels(session, now=utcnow() + offset)
        await session.commit()
        return counts


async def _shift_offer(reel_id: str, offset: timedelta):
    """Moves a reel's offer window by ``offset`` (negative = into the past)."""
    from sqlalchemy.orm import selectinload
    from app.core.database import async_session_factory
    from app.models.reel import Reel
    from app.services.reel_lifecycle_service import as_aware

    async with async_session_factory() as session:
        reel = await session.get(Reel, uuid.UUID(reel_id), options=[selectinload(Reel.coupon_template)])
        reel.expires_at = as_aware(reel.expires_at) + offset
        reel.grace_period_until = as_aware(reel.grace_period_until) + offset
        reel.coupon_template.expires_at = reel.expires_at
        await session.commit()


@pytest.mark.asyncio
async def test_cashier_without_permission_cannot_upload(client):
    store = await seed_store(with_staff=True, can_upload_reels=False)
    resp = await client.post("/api/v1/reels", json=reel_payload(), headers=bearer(store.staff_token))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_owner_grants_cashier_upload_permission(client):
    store = await seed_store(with_staff=True, can_upload_reels=False)
    grant = await client.patch(
        f"/api/v1/merchants/staff/{store.staff_id}/permissions",
        json={"can_upload_reels": True},
        headers=bearer(store.owner_token),
    )
    assert grant.status_code == 200 and grant.json()["data"]["can_upload_reels"] is True

    resp = await client.post("/api/v1/reels", json=reel_payload(), headers=bearer(store.staff_token))
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["status"] == "PENDING_MODERATION"
    reel = await _load_reel(data["reel_id"])
    assert reel.created_by_staff_id == store.staff_id
    assert reel.coupon_template is not None  # every reel carries a coupon


@pytest.mark.asyncio
async def test_other_owner_cannot_change_staff_permissions(client):
    store = await seed_store(with_staff=True)
    stranger = await seed_store()
    resp = await client.patch(
        f"/api/v1/merchants/staff/{store.staff_id}/permissions",
        json={"can_upload_reels": True},
        headers=bearer(stranger.owner_token),
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_admin_toggles_auto_approve(client):
    store = await seed_store()
    _, admin_token = await seed_user("SUPER_ADMIN", "Admin")

    forbidden = await client.patch(
        "/api/v1/admin/settings", json={"auto_approve_reels": True}, headers=bearer(store.owner_token)
    )
    assert forbidden.status_code == 403

    toggled = await client.patch(
        "/api/v1/admin/settings", json={"auto_approve_reels": True}, headers=bearer(admin_token)
    )
    assert toggled.status_code == 200
    listed = await client.get("/api/v1/admin/settings", headers=bearer(admin_token))
    assert {s["key"]: s["value"] for s in listed.json()["data"]}["auto_approve_reels"] is True

    resp = await client.post("/api/v1/reels", json=reel_payload(), headers=bearer(store.owner_token))
    assert resp.json()["data"]["status"] == "APPROVED"
    reel = await _load_reel(resp.json()["data"]["reel_id"])
    assert reel.expires_at is not None
    assert reel.coupon_template.expires_at is not None


@pytest.mark.asyncio
async def test_admin_approval_starts_offer_clock(client):
    store = await seed_store()
    _, admin_token = await seed_user("SUPER_ADMIN", "Admin")
    reel_id = (
        await client.post("/api/v1/reels", json=reel_payload(validity_days=3), headers=bearer(store.owner_token))
    ).json()["data"]["reel_id"]
    assert (await _load_reel(reel_id)).expires_at is None

    await client.post(
        f"/api/v1/admin/moderation/reels/{reel_id}/decision",
        json={"decision": "APPROVE"},
        headers=bearer(admin_token),
    )
    reel = await _load_reel(reel_id)
    from app.services.reel_lifecycle_service import as_aware
    window = as_aware(reel.grace_period_until) - as_aware(reel.expires_at)
    assert window == timedelta(hours=24)


@pytest.mark.asyncio
async def test_expired_offer_hidden_then_removed_after_grace(client):
    await set_auto_approve(True)
    store = await seed_store(latitude=19.0760, longitude=72.8777)
    _, shopper_token = await seed_user()
    reel_id = (
        await client.post("/api/v1/reels", json=reel_payload(validity_days=2), headers=bearer(store.owner_token))
    ).json()["data"]["reel_id"]
    reel = await _load_reel(reel_id)
    coupon_id = str(reel.coupon_template.id)

    await _shift_offer(reel_id, -timedelta(days=2, hours=1))  # ended an hour ago
    assert (await client.get(f"/api/v1/reels/{reel_id}")).status_code == 404
    feed = await client.get("/api/v1/reels/feed", params={"lat": 19.0760, "lon": 72.8777, "radius_km": 1})
    assert reel_id not in {item["id"] for item in feed.json()["data"]}
    claim = await client.post(f"/api/v1/coupons/{coupon_id}/claim", headers=bearer(shopper_token))
    assert claim.status_code == 410

    await _sweep_at(timedelta(0))
    expiring = await client.get("/api/v1/merchants/me/reels/expiring", headers=bearer(store.owner_token))
    assert [r["id"] for r in expiring.json()["data"]] == [reel_id]
    assert (await _load_reel(reel_id)).is_expired is True

    await _sweep_at(timedelta(hours=24))  # grace window over
    removed = await _load_reel(reel_id)
    assert removed.deleted_at is not None
    assert removed.coupon_template.is_active is False


@pytest.mark.asyncio
async def test_extension_within_grace_window_revives_offer(client):
    await set_auto_approve(True)
    store = await seed_store()
    reel_id = (
        await client.post("/api/v1/reels", json=reel_payload(validity_days=2), headers=bearer(store.owner_token))
    ).json()["data"]["reel_id"]
    await _shift_offer(reel_id, -timedelta(days=2, hours=1))
    await _sweep_at(timedelta(0))

    resp = await client.post(
        f"/api/v1/reels/{reel_id}/extend-validity",
        json={"additional_days": 30},  # FOOD caps at 5 days
        headers=bearer(store.owner_token),
    )
    assert resp.status_code == 200, resp.text
    reel = await _load_reel(reel_id)
    assert reel.is_expired is False
    assert reel.coupon_template.validity_days == 5
    assert (await client.get(f"/api/v1/reels/{reel_id}")).status_code == 200


@pytest.mark.asyncio
async def test_extension_refused_after_grace_window(client):
    await set_auto_approve(True)
    store = await seed_store()
    reel_id = (
        await client.post("/api/v1/reels", json=reel_payload(validity_days=2), headers=bearer(store.owner_token))
    ).json()["data"]["reel_id"]
    await _shift_offer(reel_id, -timedelta(days=3, hours=1))  # grace ended an hour ago

    resp = await client.post(
        f"/api/v1/reels/{reel_id}/extend-validity",
        json={"additional_days": 2},
        headers=bearer(store.owner_token),
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_my_reels_omits_deleted_and_returns_counts(client):
    await set_auto_approve(True)
    store = await seed_store()
    shopper_id, shopper_token = await seed_user()

    # Create active reel
    res1 = await client.post("/api/v1/reels", json=reel_payload(title="Active Reel"), headers=bearer(store.owner_token))
    reel_id1 = res1.json()["data"]["reel_id"]
    reel1 = await _load_reel(reel_id1)
    coupon_id = str(reel1.coupon_template.id)

    # Claim coupon
    claim_res = await client.post(f"/api/v1/coupons/{coupon_id}/claim", headers=bearer(shopper_token))
    assert claim_res.status_code == 200

    # Create second reel and delete it
    res2 = await client.post("/api/v1/reels", json=reel_payload(title="Deleted Reel"), headers=bearer(store.owner_token))
    reel_id2 = res2.json()["data"]["reel_id"]
    del_res = await client.delete(f"/api/v1/reels/{reel_id2}", headers=bearer(store.owner_token))
    assert del_res.status_code == 200

    # List my reels
    my_reels_res = await client.get("/api/v1/reels/mine", headers=bearer(store.owner_token))
    assert my_reels_res.status_code == 200
    data = my_reels_res.json()["data"]

    # Deleted reel must be omitted
    ids = [r["id"] for r in data]
    assert reel_id1 in ids
    assert reel_id2 not in ids

    # Active reel has claims_count == 1, redemptions_count == 0
    active_item = next(r for r in data if r["id"] == reel_id1)
    assert active_item["claims_count"] == 1
    assert active_item["redemptions_count"] == 0
    assert active_item["coupon"] is not None
    assert active_item["coupon"]["terms"] is not None


@pytest.mark.asyncio
async def test_expiring_reels_returns_coupon_and_counts(client):
    await set_auto_approve(True)
    store = await seed_store()
    shopper_id, shopper_token = await seed_user()

    res = await client.post("/api/v1/reels", json=reel_payload(validity_days=2), headers=bearer(store.owner_token))
    reel_id = res.json()["data"]["reel_id"]
    reel = await _load_reel(reel_id)

    # Claim coupon
    await client.post(f"/api/v1/coupons/{reel.coupon_template.id}/claim", headers=bearer(shopper_token))

    # Shift into expiring window
    await _shift_offer(reel_id, -timedelta(days=2, hours=1))
    await _sweep_at(timedelta(0))

    expiring_res = await client.get("/api/v1/merchants/me/reels/expiring", headers=bearer(store.owner_token))
    assert expiring_res.status_code == 200
    data = expiring_res.json()["data"]
    assert len(data) == 1
    exp_item = data[0]
    assert exp_item["id"] == reel_id
    assert exp_item["is_expired"] is True
    assert exp_item["claims_count"] == 1
    assert exp_item["redemptions_count"] == 0
    assert exp_item["merchant_name"] == "Feature Test Store"
    assert exp_item["coupon"] is not None


@pytest.mark.asyncio
async def test_feed_filtered_by_merchant_id_ignores_radius(client):
    await set_auto_approve(True)
    store1 = await seed_store()
    store2 = await seed_store()

    res1 = await client.post("/api/v1/reels", json=reel_payload(title="Store1 Reel"), headers=bearer(store1.owner_token))
    reel_id1 = res1.json()["data"]["reel_id"]
    res2 = await client.post("/api/v1/reels", json=reel_payload(title="Store2 Reel"), headers=bearer(store2.owner_token))
    reel_id2 = res2.json()["data"]["reel_id"]

    # Request feed with merchant_id of store1 with lat/lon far away (e.g. Delhi 28.6139, 77.2090)
    feed_res = await client.get(
        f"/api/v1/reels/feed?merchant_id={store1.merchant_id}&lat=28.6139&lon=77.2090&radius_km=1"
    )
    assert feed_res.status_code == 200
    feed_items = feed_res.json()["data"]
    feed_ids = [item["id"] for item in feed_items]
    assert reel_id1 in feed_ids
    assert reel_id2 not in feed_ids
    # Also verify logo_url is present on merchant feed summary
    assert feed_items[0]["merchant"]["logo_url"] is not None


@pytest.mark.asyncio
async def test_get_reel_returns_real_likes_count_and_logo(client):
    await set_auto_approve(True)
    store = await seed_store()
    shopper_id, shopper_token = await seed_user()

    res = await client.post("/api/v1/reels", json=reel_payload(title="Liked Reel"), headers=bearer(store.owner_token))
    reel_id = res.json()["data"]["reel_id"]

    # Initial get: 0 likes, is_liked=False
    init_res = await client.get(f"/api/v1/reels/{reel_id}", headers=bearer(shopper_token))
    assert init_res.status_code == 200
    assert init_res.json()["data"]["likes_count"] == 0
    assert init_res.json()["data"]["is_liked"] is False
    assert init_res.json()["data"]["merchant"]["logo_url"] is not None

    # Like the reel
    like_res = await client.post(f"/api/v1/reels/{reel_id}/like", headers=bearer(shopper_token))
    assert like_res.status_code == 200

    # Get reel again: 1 like, is_liked=True
    after_res = await client.get(f"/api/v1/reels/{reel_id}", headers=bearer(shopper_token))
    assert after_res.status_code == 200
    assert after_res.json()["data"]["likes_count"] == 1
    assert after_res.json()["data"]["is_liked"] is True
