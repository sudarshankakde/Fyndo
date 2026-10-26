import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from app.main import app
from app.models.user import User, UserRole
from app.models.merchant import Merchant, KycStatus, Sector
from app.core.database import async_session_factory, ensure_compatibility_schema


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_active_cities_ordering_and_aggregation(client: AsyncClient):
    await ensure_compatibility_schema()

    async with async_session_factory() as db:
        # Create unique test users and merchants in specific cities
        # City A: 1 shop (Nashik)
        # City B: 2 shops (Pune)
        # City C: 1 shop (Nagpur) -> tie with Nashik (Nagpur should come before Nashik alphabetically)
        test_suffix = uuid.uuid4().hex[:6]

        users_data = [
            ("Pune", f"+9198{uuid.uuid4().int % 100000000:08d}"),
            ("pune", f"+9198{uuid.uuid4().int % 100000000:08d}"),
            ("Nashik", f"+9198{uuid.uuid4().int % 100000000:08d}"),
            ("Nagpur", f"+9198{uuid.uuid4().int % 100000000:08d}"),
        ]

        for city_name, phone in users_data:
            user = User(
                phone=phone,
                role=UserRole.MERCHANT,
                is_active=True,
            )
            db.add(user)
            await db.flush()

            merchant = Merchant(
                user_id=user.id,
                business_name=f"Shop {city_name} {test_suffix}",
                sector=Sector.FOOD,
                address_text=f"Address in {city_name}",
                city=city_name,
                latitude=20.0,
                longitude=78.0,
                kyc_doc_url="https://doc.com/kyc.pdf",
                kyc_status=KycStatus.APPROVED,
            )
            db.add(merchant)

        await db.commit()

    # Call GET /api/v1/merchants/cities
    res = await client.get("/api/v1/merchants/cities")
    assert res.status_code == 200
    json_data = res.json()
    assert "data" in json_data
    cities_list = json_data["data"]

    # Verify Pune has count 2 (deduplicated 'Pune' and 'pune')
    pune_entry = next((c for c in cities_list if c["city"] == "Pune"), None)
    assert pune_entry is not None
    assert pune_entry["shop_count"] >= 2

    # Verify ordering: ascending by shop_count, then ascending by city name
    for i in range(len(cities_list) - 1):
        c1 = cities_list[i]
        c2 = cities_list[i + 1]
        if c1["shop_count"] == c2["shop_count"]:
            assert c1["city"] <= c2["city"], f"{c1['city']} should be <= {c2['city']} alphabetically"
        else:
            assert c1["shop_count"] < c2["shop_count"], f"Counts should be in ascending order"
