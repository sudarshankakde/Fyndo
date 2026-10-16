"""Regression tests for structured request/audit logging and the notification service.

Covers:
  * per-request correlation id assignment + echo on ``X-Request-ID``,
  * one structured access log record per request,
  * the ``fyndo.audit`` trail emitted by state-changing operations,
  * notification emission triggered by moderation decisions,
  * the inbox endpoints (list / unread-count / mark-read / mark-all-read),
  * device-token registration, re-registration and deactivation.
"""
import logging
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app

pytestmark = pytest.mark.asyncio


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


def _phone() -> str:
    return f"+91{uuid.uuid4().int % 10_000_000_000:010d}"


async def _dev_token(client: AsyncClient, role: str = "SHOPPER", phone: str = None) -> str:
    payload = {"role": role}
    if phone:
        payload["phone"] = phone
    resp = await client.post("/api/v1/auth/dev-token", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["access_token"]


async def _seed_merchant_with_pending_reel():
    """Seeds an approved merchant owning one PENDING_MODERATION reel."""
    from app.core.database import async_session_factory
    from app.models.merchant import KycStatus, Merchant, Sector
    from app.models.reel import AudioType, Reel, ReelStatus
    from app.models.user import User, UserRole

    async with async_session_factory() as session:
        owner = User(phone=_phone(), role=UserRole.MERCHANT, is_active=True)
        session.add(owner)
        await session.flush()

        merchant = Merchant(
            user_id=owner.id,
            business_name="Logging Test Store",
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

        reel = Reel(
            merchant_id=merchant.id,
            title="Logging Test Reel",
            duration_seconds=30,
            video_url="https://res.cloudinary.com/fyndo/video/upload/r.mp4",
            thumbnail_url="https://res.cloudinary.com/fyndo/image/upload/r.webp",
            audio_type=AudioType.CAMERA_MIC,
            status=ReelStatus.PENDING_MODERATION,
        )
        session.add(reel)
        await session.commit()
        return str(owner.id), str(owner.phone), str(reel.id)


# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #
async def test_response_carries_generated_request_id(client: AsyncClient):
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    request_id = resp.headers.get("x-request-id")
    assert request_id and len(request_id) == 32


async def test_supplied_request_id_is_echoed(client: AsyncClient):
    resp = await client.get("/api/v1/health", headers={"X-Request-ID": "trace-abc-123"})
    assert resp.headers.get("x-request-id") == "trace-abc-123"


async def test_every_request_emits_one_access_log(client: AsyncClient, caplog):
    caplog.set_level(logging.INFO, logger="fyndo.access")
    await client.get("/api/v1/health")

    access = [
        record for record in caplog.records
        if getattr(record, "event", None) == "http_request"
    ]
    assert len(access) == 1
    record = access[0]
    assert record.status_code == 200
    assert record.path == "/api/v1/health"
    assert record.http_method == "GET"
    assert record.duration_ms >= 0
    # Correlation ids are stamped onto the record by the context filter.
    assert record.request_id == "-" or isinstance(record.request_id, str)


async def test_audit_trail_is_structured(caplog):
    from app.core.audit import audit_log

    caplog.set_level(logging.INFO, logger="fyndo.audit")
    actor = uuid.uuid4()
    audit_log("reel.moderate", actor_id=actor, actor_role="SUPER_ADMIN",
              target_type="reel", target_id=uuid.uuid4(), decision="APPROVE")

    records = [r for r in caplog.records if getattr(r, "event", None) == "audit"]
    assert len(records) == 1
    record = records[0]
    assert record.action == "reel.moderate"
    assert record.outcome == "success"
    assert record.actor_id == str(actor)
    assert record.detail_decision == "APPROVE"


async def test_logging_configuration_is_idempotent():
    from app.core.logging_config import configure_logging

    configure_logging()  # second call must be a no-op and must not raise
    assert logging.getLogger("fyndo.audit").handlers


# --------------------------------------------------------------------------- #
# Notifications
# --------------------------------------------------------------------------- #
async def test_moderation_decision_notifies_merchant_and_audits(client: AsyncClient, caplog):
    caplog.set_level(logging.INFO)
    owner_id, owner_phone, reel_id = await _seed_merchant_with_pending_reel()
    admin_token = await _dev_token(client, "SUPER_ADMIN")

    decision = await client.post(
        f"/api/v1/admin/moderation/reels/{reel_id}/decision",
        json={"decision": "APPROVE"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert decision.status_code == 200, decision.text

    assert any(
        getattr(r, "action", None) == "reel.moderate"
        for r in caplog.records
    ), "moderation decision must be audit-logged"

    # The store owner now has exactly one unread alert.
    owner_token = await _dev_token(client, "SHOPPER", owner_phone)
    headers = {"Authorization": f"Bearer {owner_token}"}

    unread = await client.get("/api/v1/notifications/unread-count", headers=headers)
    assert unread.json()["data"]["unread_count"] == 1

    inbox = await client.get("/api/v1/notifications", headers=headers)
    page = inbox.json()["data"]
    assert len(page["items"]) == 1
    alert = page["items"][0]
    assert alert["event_type"] == "reel_approved"
    assert alert["action_ref"] == reel_id
    assert alert["is_read"] is False

    # Marking it read flips the badge.
    read = await client.post(f"/api/v1/notifications/{alert['id']}/read", headers=headers)
    assert read.status_code == 200
    assert read.json()["data"]["is_read"] is True
    unread = await client.get("/api/v1/notifications/unread-count", headers=headers)
    assert unread.json()["data"]["unread_count"] == 0

    # Unknown ids are reported as 404 rather than silently succeeding.
    missing = await client.post(
        f"/api/v1/notifications/{uuid.uuid4()}/read", headers=headers
    )
    assert missing.status_code == 404


async def test_inbox_paginates_and_marks_all_read(client: AsyncClient):
    from app.core.database import async_session_factory
    from app.models.notification import Notification
    from app.models.user import User, UserRole

    async with async_session_factory() as session:
        shopper = User(phone=_phone(), role=UserRole.SHOPPER, is_active=True)
        session.add(shopper)
        await session.flush()
        for index in range(5):
            session.add(
                Notification(
                    user_id=shopper.id,
                    category="UPDATES",
                    event_type="seed",
                    title=f"Alert {index}",
                    body="Body",
                )
            )
        await session.commit()
        shopper_phone = shopper.phone

    token = await _dev_token(client, "SHOPPER", shopper_phone)
    headers = {"Authorization": f"Bearer {token}"}

    first = await client.get("/api/v1/notifications?limit=2", headers=headers)
    page = first.json()["data"]
    assert len(page["items"]) == 2
    assert page["has_more"] is True
    assert page["next_cursor"]

    second = await client.get(
        f"/api/v1/notifications?limit=2&cursor={page['next_cursor']}", headers=headers
    )
    second_page = second.json()["data"]
    assert len(second_page["items"]) == 2
    ids = {item["id"] for item in page["items"]} | {
        item["id"] for item in second_page["items"]
    }
    assert len(ids) == 4  # cursor pages never overlap

    marked = await client.post("/api/v1/notifications/read-all", headers=headers)
    assert marked.json()["data"]["updated"] == 5
    unread = await client.get("/api/v1/notifications/unread-count", headers=headers)
    assert unread.json()["data"]["unread_count"] == 0


async def test_device_token_lifecycle(client: AsyncClient):
    token = await _dev_token(client, "SHOPPER")
    headers = {"Authorization": f"Bearer {token}"}
    device = f"ExponentPushToken[{uuid.uuid4().hex}]"

    created = await client.post(
        "/api/v1/notifications/device-token",
        json={"token": device, "platform": "ANDROID"},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    device_id = created.json()["data"]["id"]

    # Re-registering the same device updates in place instead of duplicating.
    again = await client.post(
        "/api/v1/notifications/device-token",
        json={"token": device, "platform": "IOS"},
        headers=headers,
    )
    assert again.status_code == 201
    assert again.json()["data"]["id"] == device_id
    assert again.json()["data"]["platform"] == "IOS"

    removed = await client.post(
        "/api/v1/notifications/device-token/unregister",
        json={"token": device},
        headers=headers,
    )
    assert removed.json()["data"]["removed"] is True

    again_removed = await client.post(
        "/api/v1/notifications/device-token/unregister",
        json={"token": device},
        headers=headers,
    )
    assert again_removed.json()["data"]["removed"] is False


async def test_inbox_requires_authentication(client: AsyncClient):
    resp = await client.get("/api/v1/notifications")
    assert resp.status_code in (401, 403)
