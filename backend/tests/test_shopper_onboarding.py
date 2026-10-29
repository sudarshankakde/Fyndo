import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.models.user import User, UserRole
from app.core.database import async_session_factory, ensure_compatibility_schema
from app.core.security import create_access_token


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_shopper_onboarding_completeness_flow(client: AsyncClient):
    # 1. Create a fresh Shopper in database with unique phone
    phone = f"+919{uuid.uuid4().int % 1000000000:09d}"
    await ensure_compatibility_schema()
    async with async_session_factory() as db:
        user = User(
            phone=phone,
            role=UserRole.SHOPPER,
            preferred_language="en",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        user_id = user.id

    token = create_access_token(subject=str(user_id), role="SHOPPER")
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Check /auth/me initially: onboarding_completed must be False
    res = await client.get("/api/v1/auth/me", headers=headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["onboarding_completed"] is False
    assert data["full_name"] is None
    assert data["latitude"] is None

    # 3. Partial save: Step 1 (name and preferences)
    res = await client.patch(
        "/api/v1/auth/profile",
        headers=headers,
        json={
            "full_name": "Priya Sharma",
            "shopping_preferences": ["FASHION_CLOTHING", "CAFE_COFFEE_SHOPS"],
        },
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["full_name"] == "Priya Sharma"
    assert data["shopping_preferences"] == ["FASHION_CLOTHING", "CAFE_COFFEE_SHOPS"]
    # Still incomplete because location is missing
    assert data["onboarding_completed"] is False

    # 4. Attempt to send invalid latitude (> 90) -> should be rejected
    res = await client.patch(
        "/api/v1/auth/profile",
        headers=headers,
        json={"latitude": 150.0},
    )
    assert res.status_code == 422

    # 5. Step 2: Save validated location
    res = await client.patch(
        "/api/v1/auth/profile",
        headers=headers,
        json={
            "latitude": 21.1458,
            "longitude": 79.0882,
            "city": "Nagpur",
            "address_text": "42, Civil Lines, Opposite High Court",
            "pincode": "440001",
        },
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["latitude"] == 21.1458
    assert data["longitude"] == 79.0882
    assert data["city"] == "Nagpur"
    assert data["address_text"] == "42, Civil Lines, Opposite High Court"
    assert data["pincode"] == "440001"
    # Now all required fields are present -> onboarding_completed must be True!
    assert data["onboarding_completed"] is True

    # 6. Verify GET /auth/me persists this state
    res = await client.get("/api/v1/auth/me", headers=headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["onboarding_completed"] is True
    assert data["full_name"] == "Priya Sharma"
    assert data["city"] == "Nagpur"


@pytest.mark.asyncio
async def test_merchant_and_cashier_bypass_shopper_onboarding(client: AsyncClient):
    # Merchant user
    phone = f"+919{uuid.uuid4().int % 1000000000:09d}"
    async with async_session_factory() as db:
        merchant_user = User(
            phone=phone,
            role=UserRole.MERCHANT,
            preferred_language="en",
            onboarding_completed=True,
        )
        db.add(merchant_user)
        await db.commit()
        await db.refresh(merchant_user)
        m_id = merchant_user.id

    token = create_access_token(subject=str(m_id), role="MERCHANT")
    res = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()["data"]
    # Merchants must never be blocked by Shopper onboarding
    assert data["onboarding_completed"] is True
