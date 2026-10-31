"""Tests for the super admin notification broadcast and dispatch console."""
import uuid
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.admin.deps import issue_session
from app.core.database import async_session_factory
from app.main import app
from app.models.audit_log import AuditLog
from app.models.notification import DevicePlatform, DeviceToken, Notification
from app.models.user import User, UserRole
from tests.feature_helpers import prepare_schema, seed_user, unique_phone


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest.mark.asyncio
async def test_broadcast_view_unauthenticated_redirect(client: AsyncClient):
    """Anonymous requests redirect to the admin login page."""
    resp = await client.get("/admin/broadcast", follow_redirects=False)
    assert resp.status_code == 303
    assert "/admin/login" in resp.headers["location"]


@pytest.mark.asyncio
async def test_broadcast_view_authenticated(client: AsyncClient):
    """Authenticated super admin receives 200 OK with composer and stats."""
    await prepare_schema()
    session_cookie = issue_session("+919999900000")
    client.cookies.set("fyndo_admin_session", session_cookie)

    resp = await client.get("/admin/broadcast")
    assert resp.status_code == 200
    assert "Notification Broadcast & Dispatch" in resp.text
    assert "Target Audience" in resp.text
    assert "Compose New Broadcast" in resp.text
    assert "Push Gateway Status" in resp.text


@pytest.mark.asyncio
async def test_broadcast_send_to_merchants(client: AsyncClient):
    """Dispatches in-app notifications and records audit log for all active merchants."""
    await prepare_schema()
    m_uid1, _ = await seed_user("MERCHANT", "Merchant One")
    m_uid2, _ = await seed_user("MERCHANT", "Merchant Two")
    s_uid, _ = await seed_user("SHOPPER", "Shopper One")

    session_cookie = issue_session("+919999900000")
    client.cookies.set("fyndo_admin_session", session_cookie)

    payload = {
        "audience": "MERCHANT",
        "title": "Merchant Platform Update",
        "body": "Important policy changes are in effect.",
        "category": "UPDATES",
        "send_push": "true",
    }
    resp = await client.post("/admin/broadcast/send", data=payload, follow_redirects=False)
    assert resp.status_code == 303
    assert "ok=" in resp.headers["location"]

    # Verify notifications created in database for merchants
    async with async_session_factory() as s:
        notifs = (
            await s.execute(
                select(Notification).where(Notification.title == "Merchant Platform Update")
            )
        ).scalars().all()
        recipient_ids = {n.user_id for n in notifs}
        assert m_uid1 in recipient_ids
        assert m_uid2 in recipient_ids
        assert s_uid not in recipient_ids

        # Verify audit log recorded
        audit = (
            await s.execute(
                select(AuditLog).where(AuditLog.action == "notification.broadcast")
            )
        ).scalars().first()
        assert audit is not None
        assert audit.target_id == "MERCHANT"


@pytest.mark.asyncio
async def test_broadcast_send_to_single_user_by_uuid(client: AsyncClient):
    """Dispatches notification to a specific user identified by user ID."""
    await prepare_schema()
    target_uid, _ = await seed_user("SHOPPER", "Specific User")

    session_cookie = issue_session("+919999900000")
    client.cookies.set("fyndo_admin_session", session_cookie)

    payload = {
        "audience": "USER",
        "target_user": str(target_uid),
        "title": "Exclusive Flash Deal For You",
        "body": "Tap to view your 50% off coupon.",
        "category": "DEALS",
        "send_push": "true",
        "action_type": "screen",
        "action_ref": "Wallet",
    }
    resp = await client.post("/admin/broadcast/send", data=payload, follow_redirects=False)
    assert resp.status_code == 303
    assert "ok=" in resp.headers["location"]

    async with async_session_factory() as s:
        notif = (
            await s.execute(
                select(Notification).where(
                    Notification.user_id == target_uid,
                    Notification.title == "Exclusive Flash Deal For You",
                )
            )
        ).scalars().first()
        assert notif is not None
        assert notif.category == "DEALS"
        assert notif.action_type == "screen"
        assert notif.action_ref == "Wallet"


@pytest.mark.asyncio
async def test_broadcast_send_validation_errors(client: AsyncClient):
    """Empty title/body or missing specific user returns clean error redirect."""
    await prepare_schema()
    session_cookie = issue_session("+919999900000")
    client.cookies.set("fyndo_admin_session", session_cookie)

    # Missing title
    resp1 = await client.post(
        "/admin/broadcast/send",
        data={"audience": "ALL", "title": "", "body": "Some body"},
        follow_redirects=False,
    )
    assert resp1.status_code == 303
    assert "err=" in resp1.headers["location"]

    # Missing user identifier when audience == USER
    resp2 = await client.post(
        "/admin/broadcast/send",
        data={"audience": "USER", "target_user": "", "title": "Hi", "body": "Hello"},
        follow_redirects=False,
    )
    assert resp2.status_code == 303
    assert "err=" in resp2.headers["location"]
