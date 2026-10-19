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
