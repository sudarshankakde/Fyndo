import uuid
from datetime import timedelta
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.reel_lifecycle_service import utcnow
from tests.feature_helpers import (
    bearer,
    prepare_schema,
    reel_payload,
    seed_store,
    set_auto_approve,
)


@pytest_asyncio.fixture(autouse=True)
async def init_db():
    await prepare_schema()
    await set_auto_approve(True)
    yield
    await set_auto_approve(False)


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_update_reel_coupon_fields(client):
    store = await seed_store()
    payload = reel_payload(title="Original Offer")
    payload["coupon"]["discount_value"] = 20.0
    payload["coupon"]["min_order_amount"] = 100.0

    create_res = await client.post("/api/v1/reels", json=payload, headers=bearer(store.owner_token))
    assert create_res.status_code == 200
    reel_id = create_res.json()["data"]["reel_id"]

    patch_payload = {
        "title": "Summer Flash Sale",
        "discount_value": 35.0,
        "discount_type": "FLAT_AMOUNT",
        "min_order_amount": 500.0,
        "terms": "Valid only on dine-in bill above Rs 500",
    }
    update_res = await client.patch(
        f"/api/v1/reels/{reel_id}",
        json=patch_payload,
        headers=bearer(store.owner_token),
    )
    assert update_res.status_code == 200
    data = update_res.json()["data"]
    assert data["title"] == "Summer Flash Sale"
    assert data["coupon"]["discount_value"] == 35.0
    assert data["coupon"]["discount_type"] == "FLAT_AMOUNT"
    assert data["coupon"]["min_order_amount"] == 500.0
    assert data["coupon"]["terms"] == "Valid only on dine-in bill above Rs 500"


@pytest.mark.asyncio
async def test_update_reel_expiry_extension(client):
    store = await seed_store()
    payload = reel_payload(title="Extendable Reel")
    payload["coupon"]["validity_days"] = 2

    create_res = await client.post("/api/v1/reels", json=payload, headers=bearer(store.owner_token))
    assert create_res.status_code == 200
    reel_id = create_res.json()["data"]["reel_id"]

    # Food sector allows up to 5 days. Extend to now + 4 days.
    now = utcnow()
    new_expiry = (now + timedelta(days=4)).isoformat()

    update_res = await client.patch(
        f"/api/v1/reels/{reel_id}",
        json={"expires_at": new_expiry},
        headers=bearer(store.owner_token),
    )
    assert update_res.status_code == 200
    data = update_res.json()["data"]
    assert data["expires_at"] is not None
    assert data["coupon"]["validity_days"] >= 3


@pytest.mark.asyncio
async def test_update_reel_expiry_validation_errors(client):
    store = await seed_store()
    payload = reel_payload(title="Validation Reel")
    payload["coupon"]["validity_days"] = 3

    create_res = await client.post("/api/v1/reels", json=payload, headers=bearer(store.owner_token))
    reel_id = create_res.json()["data"]["reel_id"]

    now = utcnow()
    # 1. Past date
    past_expiry = (now - timedelta(days=1)).isoformat()
    res_past = await client.patch(
        f"/api/v1/reels/{reel_id}",
        json={"expires_at": past_expiry},
        headers=bearer(store.owner_token),
    )
    assert res_past.status_code == 400

    # 2. Earlier than current expiry
    earlier_expiry = (now + timedelta(days=1)).isoformat()
    res_earlier = await client.patch(
        f"/api/v1/reels/{reel_id}",
        json={"expires_at": earlier_expiry},
        headers=bearer(store.owner_token),
    )
    assert res_earlier.status_code == 400
    assert "later than the current expiry date" in res_earlier.text

    # 3. Exceeding sector limit (Food is capped at 5 days)
    too_long_expiry = (now + timedelta(days=10)).isoformat()
    res_exceed = await client.patch(
        f"/api/v1/reels/{reel_id}",
        json={"expires_at": too_long_expiry},
        headers=bearer(store.owner_token),
    )
    assert res_exceed.status_code == 400
    assert "cannot exceed maximum validity" in res_exceed.text


@pytest.mark.asyncio
async def test_update_reel_with_same_expiry_date(client):
    """Verifies that submitting the current expiry date (e.g. from an edit form) does not trigger extension validation errors."""
    store = await seed_store()
    payload = reel_payload(title="Same Expiry Offer")
    payload["coupon"]["validity_days"] = 3

    create_res = await client.post("/api/v1/reels", json=payload, headers=bearer(store.owner_token))
    assert create_res.status_code == 200
    reel_id = create_res.json()["data"]["reel_id"]

    # Fetch reel details to get current expires_at
    get_res = await client.get(f"/api/v1/reels/{reel_id}", headers=bearer(store.owner_token))
    assert get_res.status_code == 200
    current_expiry = get_res.json()["data"]["coupon"]["expires_at"]

    # Update title and min order amount while passing the existing expires_at
    update_res = await client.patch(
        f"/api/v1/reels/{reel_id}",
        json={
            "title": "Same Expiry Offer Renamed",
            "min_order_amount": 250.0,
            "expires_at": current_expiry,
        },
        headers=bearer(store.owner_token),
    )
    assert update_res.status_code == 200
    data = update_res.json()["data"]
    assert data["title"] == "Same Expiry Offer Renamed"
    assert data["coupon"]["min_order_amount"] == 250.0


@pytest.mark.asyncio
async def test_update_reel_caption_and_inactive_subscription(client):
    """Verifies caption fallback and subscription enforcement on expiry extension."""
    from app.core.database import async_session_factory
    from app.models.merchant import Merchant, SubscriptionStatus

    # Create store with active subscription first to create the reel
    store = await seed_store()
    payload = reel_payload(title="Initial Title")
    payload["coupon"]["validity_days"] = 2

    create_res = await client.post("/api/v1/reels", json=payload, headers=bearer(store.owner_token))
    assert create_res.status_code == 200
    reel_id = create_res.json()["data"]["reel_id"]

    # 1. Caption updates title
    update_caption = await client.patch(
        f"/api/v1/reels/{reel_id}",
        json={"caption": "Updated Via Caption"},
        headers=bearer(store.owner_token),
    )
    assert update_caption.status_code == 200
    assert update_caption.json()["data"]["title"] == "Updated Via Caption"

    # Now expire the store subscription
    async with async_session_factory() as db:
        merchant = await db.get(Merchant, store.merchant_id)
        merchant.subscription_status = SubscriptionStatus.EXPIRED
        await db.commit()

    # 2. Extending expiry with expired subscription raises 403
    future_expiry = (utcnow() + timedelta(days=4)).isoformat()
    update_sub = await client.patch(
        f"/api/v1/reels/{reel_id}",
        json={"expires_at": future_expiry},
        headers=bearer(store.owner_token),
    )
    assert update_sub.status_code == 403
    assert "subscription" in update_sub.text.lower()
