"""Shared helper functions and fixtures for E2E subscription tests."""
import uuid
from datetime import datetime, timezone
from typing import Optional, Tuple

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.database import async_session_factory
from app.core.security import create_access_token
from app.main import app
from app.models.merchant import KycStatus, Merchant, Sector
from app.models.user import User, UserRole
from tests.feature_helpers import (
    bearer,
    prepare_schema,
    reel_payload,
    seed_store,
    seed_user,
    set_auto_approve,
    set_auto_approve_kyc,
    unique_phone,
)


def utcnow() -> datetime:
    """Returns current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def parse_iso_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    """Parses an ISO format datetime string into timezone-aware datetime."""
    if not dt_str:
        return None
    # Replace trailing 'Z' with UTC offset if needed
    cleaned = dt_str.replace("Z", "+00:00")
    dt = datetime.fromisoformat(cleaned)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


async def seed_admin(full_name: str = "Test Platform Admin") -> Tuple[uuid.UUID, str]:
    """Creates a Super Admin user and returns (user_id, access_token)."""
    async with async_session_factory() as session:
        user = User(
            phone=unique_phone(),
            full_name=full_name,
            role=UserRole.SUPER_ADMIN,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        token = create_access_token(subject=str(user.id), role=UserRole.SUPER_ADMIN.value)
        return user.id, token


async def onboard_merchant_via_api(
    client: AsyncClient,
    user_token: Optional[str] = None,
    business_name: str = "Subscription Store",
    sector: str = "FOOD",
    city: str = "Nagpur",
) -> Tuple[uuid.UUID, str, dict]:
    """Registers a new user and onboards merchant via POST /api/v1/merchants/onboard.
    
    Returns (user_id, user_token, onboard_response_json).
    """
    if not user_token:
        user_id, user_token = await seed_user("MERCHANT", "Merchant Owner")
    else:
        user_id = uuid.uuid4()

    payload = {
        "business_name": business_name,
        "sector": sector,
        "address_text": "123 Central Avenue, Sitabuldi",
        "city": city,
        "latitude": 21.1458,
        "longitude": 79.0882,
        "gstin": "27AAAAA0000A1Z5",
        "kyc_doc_url": "https://res.cloudinary.com/fyndo/kyc/sample.pdf",
    }
    resp = await client.post(
        "/api/v1/merchants/onboard",
        json=payload,
        headers=bearer(user_token),
    )
    return user_id, user_token, resp.json()


async def set_subscription_in_db(
    merchant_id: uuid.UUID,
    status: str = "ACTIVE",
    expires_at: Optional[datetime] = None,
    start_date: Optional[datetime] = None,
) -> None:
    """Directly sets merchant subscription columns in DB for boundary setup."""
    async with async_session_factory() as session:
        merchant = await session.get(Merchant, merchant_id)
        if merchant:
            if hasattr(merchant, "subscription_status"):
                setattr(merchant, "subscription_status", status)
            if hasattr(merchant, "subscription_expires_at"):
                setattr(merchant, "subscription_expires_at", expires_at)
            if hasattr(merchant, "subscription_start_date") and start_date is not None:
                setattr(merchant, "subscription_start_date", start_date)
            await session.commit()


def assert_error_envelope(
    resp_json: dict,
    expected_status_code: int = 403,
    expected_code: str = "HTTP_403",
    expected_message: Optional[str] = None,
) -> None:
    """Verifies that an error response matches the Fyndo ErrorEnvelope contract."""
    assert resp_json.get("success") is False, f"Expected success=False, got: {resp_json}"
    err = resp_json.get("error", {})
    assert err.get("code") == expected_code, f"Expected error.code={expected_code}, got: {err.get('code')}"
    if expected_message:
        msg = err.get("message", "")
        assert expected_message.lower() in msg.lower(), (
            f"Expected '{expected_message}' in error message, got: '{msg}'"
        )
