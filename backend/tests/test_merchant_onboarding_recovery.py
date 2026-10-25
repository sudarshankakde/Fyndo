"""Integration tests for Merchant Onboarding Interruption, Recovery, and Idempotency.

Covers:
1. Customer without store starting merchant onboarding without premature role upgrade.
2. Saving, updating, and retrieving server-side onboarding drafts.
3. User isolation / ownership verification of drafts.
4. Atomic store onboarding upgrading user role to MERCHANT and deleting draft.
5. Idempotent submission preventing duplicate merchant stores upon network retries.
6. Existing merchant rejected on Customer login.
"""
import uuid
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.config import settings
from app.core.database import async_session_factory, Base, engine, ensure_compatibility_schema
from app.main import app
from app.models.merchant import Merchant, MerchantOnboardingDraft, KycStatus, Sector
from app.models.user import User, UserRole


def unique_phone() -> str:
    return f"+9198{uuid.uuid4().int % 100_000_000:08d}"


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _login(client: AsyncClient, phone: str, role: str = "merchant") -> dict:
    send = await client.post("/api/v1/auth/otp/send", json={"phone": phone, "role": role})
    assert send.status_code == 200
    otp = send.json()["data"]["test_otp"]
    verify = await client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": phone, "otp": otp, "role": role, "preferred_language": "en"}
    )
    assert verify.status_code == 200
    return verify.json()["data"]


@pytest.mark.asyncio
async def test_customer_eligible_for_merchant_login_and_initial_draft(client: AsyncClient):
    phone = unique_phone()
    auth_data = await _login(client, phone, role="merchant")
    token = auth_data["access_token"]
    user = auth_data["user"]

    # Role remains SHOPPER until store registration succeeds
    assert user["role"] == "SHOPPER"

    # User initially has no draft
    headers = {"Authorization": f"Bearer {token}"}
    draft_res = await client.get("/api/v1/merchants/onboard/draft", headers=headers)
    assert draft_res.status_code == 200
    data = draft_res.json()["data"]
    assert data["has_draft"] is False
    assert data["step"] == 1


@pytest.mark.asyncio
async def test_save_update_and_retrieve_draft(client: AsyncClient):
    phone = unique_phone()
    auth_data = await _login(client, phone, role="merchant")
    token = auth_data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Step 1: Save basic details
    save_res = await client.put(
        "/api/v1/merchants/onboard/draft",
        headers=headers,
        json={
            "step": 2,
            "business_name": "Nagpur Sweets & Bakery",
            "sector": "FOOD_BEVERAGE",
            "description": "Finest traditional sweets in Sitabuldi",
        }
    )
    assert save_res.status_code == 200
    draft1 = save_res.json()["data"]
    assert draft1["has_draft"] is True
    assert draft1["step"] == 2
    assert draft1["business_name"] == "Nagpur Sweets & Bakery"
    assert draft1["sector"] == "FOOD_BEVERAGE"

    # Step 2: Update with location and documents
    update_res = await client.put(
        "/api/v1/merchants/onboard/draft",
        headers=headers,
        json={
            "step": 3,
            "address_text": "Plot 42, Main Road, Sitabuldi",
            "city": "Nagpur",
            "pincode": "440012",
            "latitude": 21.1458,
            "longitude": 79.0882,
            "gstin": "27ABCDE1234F1Z5",
            "kyc_doc_url": "https://res.cloudinary.com/fyndo/image/upload/v1/trade_license.jpg",
        }
    )
    assert update_res.status_code == 200
    draft2 = update_res.json()["data"]
    assert draft2["step"] == 3
    assert draft2["business_name"] == "Nagpur Sweets & Bakery"
    assert draft2["address_text"] == "Plot 42, Main Road, Sitabuldi"
    assert draft2["city"] == "Nagpur"
    assert draft2["pincode"] == "440012"
    assert draft2["kyc_doc_url"] == "https://res.cloudinary.com/fyndo/image/upload/v1/trade_license.jpg"

    # Retrieve draft via GET to verify persistence
    get_res = await client.get("/api/v1/merchants/onboard/draft", headers=headers)
    assert get_res.status_code == 200
    retrieved = get_res.json()["data"]
    assert retrieved["has_draft"] is True
    assert retrieved["step"] == 3
    assert retrieved["business_name"] == "Nagpur Sweets & Bakery"


@pytest.mark.asyncio
async def test_draft_ownership_isolation(client: AsyncClient):
    phone_a = unique_phone()
    auth_a = await _login(client, phone_a, role="merchant")
    headers_a = {"Authorization": f"Bearer {auth_a['access_token']}"}

    # User A saves a draft
    await client.put(
        "/api/v1/merchants/onboard/draft",
        headers=headers_a,
        json={"step": 2, "business_name": "User A Store"}
    )

    # User B logs in
    phone_b = unique_phone()
    auth_b = await _login(client, phone_b, role="merchant")
    headers_b = {"Authorization": f"Bearer {auth_b['access_token']}"}

    # User B should NOT see User A's draft
    draft_b_res = await client.get("/api/v1/merchants/onboard/draft", headers=headers_b)
    assert draft_b_res.status_code == 200
    draft_b = draft_b_res.json()["data"]
    assert draft_b["has_draft"] is False
    assert draft_b["business_name"] is None


@pytest.mark.asyncio
async def test_atomic_onboard_upgrades_role_and_cleans_draft(client: AsyncClient):
    phone = unique_phone()
    auth_data = await _login(client, phone, role="merchant")
    token = auth_data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Save draft
    await client.put(
        "/api/v1/merchants/onboard/draft",
        headers=headers,
        json={
            "step": 3,
            "business_name": "Royal Footwear",
            "sector": "FOOTWEAR",
            "address_text": "Shop 12, Dharampeth Market",
            "city": "Nagpur",
            "pincode": "440010",
            "latitude": 21.1400,
            "longitude": 79.0700,
            "kyc_doc_url": "https://res.cloudinary.com/fyndo/image/upload/v1/doc.jpg",
        }
    )

    # 2. Final store onboarding submission
    onboard_payload = {
        "business_name": "Royal Footwear",
        "sector": "FOOTWEAR",
        "address_text": "Shop 12, Dharampeth Market",
        "city": "Nagpur",
        "latitude": 21.1400,
        "longitude": 79.0700,
        "gstin": "27ABCDE9999F1Z9",
        "kyc_doc_url": "https://res.cloudinary.com/fyndo/image/upload/v1/doc.jpg",
    }
    onboard_res = await client.post("/api/v1/merchants/onboard", headers=headers, json=onboard_payload)
    assert onboard_res.status_code == 200
    merchant_data = onboard_res.json()["data"]
    assert merchant_data["business_name"] == "Royal Footwear"

    # 3. Verify user role is now MERCHANT
    me_res = await client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["data"]["role"] == "MERCHANT"

    # 4. Verify draft is cleaned up atomically
    draft_res = await client.get("/api/v1/merchants/onboard/draft", headers=headers)
    assert draft_res.status_code == 200
    assert draft_res.json()["data"]["has_draft"] is False


@pytest.mark.asyncio
async def test_idempotent_onboard_submission(client: AsyncClient):
    phone = unique_phone()
    auth_data = await _login(client, phone, role="merchant")
    token = auth_data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "business_name": "Idempotent Store",
        "sector": "ELECTRONICS",
        "address_text": "100 Tech Park, IT Park Road",
        "city": "Nagpur",
        "latitude": 21.1200,
        "longitude": 79.0500,
        "kyc_doc_url": "https://res.cloudinary.com/fyndo/image/upload/v1/cert.jpg",
    }

    # First submission
    res1 = await client.post("/api/v1/merchants/onboard", headers=headers, json=payload)
    assert res1.status_code == 200
    merchant_id = res1.json()["data"]["id"]

    # Second submission (retry scenario)
    res2 = await client.post("/api/v1/merchants/onboard", headers=headers, json=payload)
    assert res2.status_code == 200
    assert res2.json()["data"]["id"] == merchant_id
    assert res2.json()["message"] == "Merchant profile already exists."


@pytest.mark.asyncio
async def test_existing_merchant_rejected_on_customer_login(client: AsyncClient):
    phone = unique_phone()
    # 1. Onboard as merchant
    auth_data = await _login(client, phone, role="merchant")
    headers = {"Authorization": f"Bearer {auth_data['access_token']}"}
    await client.post(
        "/api/v1/merchants/onboard",
        headers=headers,
        json={
            "business_name": "Active Merchant Store",
            "sector": "FASHION_CLOTHING",
            "address_text": "Wardha Road, Nagpur",
            "city": "Nagpur",
            "latitude": 21.1000,
            "longitude": 79.0800,
            "kyc_doc_url": "https://res.cloudinary.com/fyndo/image/upload/v1/doc.jpg",
        }
    )

    # 2. Attempting to send OTP as customer must be rejected immediately with 400
    send = await client.post("/api/v1/auth/otp/send", json={"phone": phone, "role": "customer"})
    print("SEND RESPONSE:", send.text)
    assert send.status_code == 400
    assert "registered as a Merchant account" in send.text



