import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from app.core.config import settings
from app.main import app


@pytest_asyncio.fixture(autouse=True)
async def init_db():
    from app.core.database import Base, engine
    import app.models  # Ensure models are loaded
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_send_and_verify_otp_flow(client: AsyncClient):
    phone = "+919811223344"

    # Send OTP
    send_res = await client.post("/api/v1/auth/otp/send", json={"phone": phone, "channel": "SMS"})
    assert send_res.status_code == 200
    send_data = send_res.json()
    assert send_data["success"] is True
    test_otp = send_data["data"]["test_otp"]
    assert test_otp is not None

    # Verify OTP
    verify_res = await client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": phone, "otp": test_otp, "preferred_language": "mr"}
    )
    assert verify_res.status_code == 200
    verify_data = verify_res.json()
    assert verify_data["success"] is True
    access_token = verify_data["data"]["access_token"]
    refresh_token = verify_data["data"]["refresh_token"]
    user = verify_data["data"]["user"]
    assert user["phone"] == phone
    assert user["preferred_language"] == "mr"
    assert user["role"] == "SHOPPER"

    # Get Me with access token
    me_res = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert me_res.status_code == 200
    assert me_res.json()["data"]["phone"] == phone


@pytest.mark.asyncio
async def test_otp_replay_prevention(client: AsyncClient):
    phone = "+919811223355"
    send_res = await client.post("/api/v1/auth/otp/send", json={"phone": phone})
    otp = send_res.json()["data"]["test_otp"]

    # First verification should succeed
    res1 = await client.post("/api/v1/auth/otp/verify", json={"phone": phone, "otp": otp})
    assert res1.status_code == 200

    # Second attempt with same OTP must fail (replay protection)
    res2 = await client.post("/api/v1/auth/otp/verify", json={"phone": phone, "otp": otp})
    assert res2.status_code == 400


@pytest.mark.asyncio
async def test_invalid_otp_code(client: AsyncClient):
    phone = "+919811223366"
    await client.post("/api/v1/auth/otp/send", json={"phone": phone})

    bad_res = await client.post("/api/v1/auth/otp/verify", json={"phone": phone, "otp": "000000"})
    assert bad_res.status_code == 400


@pytest.mark.asyncio
async def test_admin_login_and_privileges(client: AsyncClient):
    # Valid Admin Login
    admin_res = await client.post(
        "/api/v1/auth/admin-login",
        json={
            "identifier": settings.SUPER_ADMIN_IDENTIFIER,
            "password": settings.SUPER_ADMIN_PASSWORD
        }
    )
    assert admin_res.status_code == 200
    admin_data = admin_res.json()
    assert admin_data["success"] is True
    assert admin_data["data"]["user"]["role"] == "SUPER_ADMIN"
    admin_token = admin_data["data"]["access_token"]

    # Admin access to pending moderation queue
    queue_res = await client.get(
        "/api/v1/admin/moderation/reels",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert queue_res.status_code == 200

    # Invalid password attempt
    bad_res = await client.post(
        "/api/v1/auth/admin-login",
        json={
            "identifier": settings.SUPER_ADMIN_IDENTIFIER,
            "password": "WrongPassword123"
        }
    )
    assert bad_res.status_code == 401


@pytest.mark.asyncio
async def test_token_refresh_and_logout_flow(client: AsyncClient):
    phone = "+919811223377"
    send_res = await client.post("/api/v1/auth/otp/send", json={"phone": phone})
    otp = send_res.json()["data"]["test_otp"]
    auth_res = await client.post("/api/v1/auth/otp/verify", json={"phone": phone, "otp": otp})
    tokens = auth_res.json()["data"]

    refresh_token = tokens["refresh_token"]

    # Refresh tokens
    ref_res = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert ref_res.status_code == 200
    new_tokens = ref_res.json()["data"]
    new_access = new_tokens["access_token"]
    new_refresh = new_tokens["refresh_token"]

    # Verify new access token works
    me_res = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {new_access}"})
    assert me_res.status_code == 200

    # Old refresh token should be revoked (rotation)
    old_ref_res = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert old_ref_res.status_code == 401

    # Logout with active refresh token
    logout_res = await client.post("/api/v1/auth/logout", json={"refresh_token": new_refresh})
    assert logout_res.status_code == 200

    # Refresh after logout should fail
    after_logout_ref = await client.post("/api/v1/auth/refresh", json={"refresh_token": new_refresh})
    assert after_logout_ref.status_code == 401


@pytest.mark.asyncio
async def test_patch_profile(client: AsyncClient):
    phone = "+919811223388"
    send_res = await client.post("/api/v1/auth/otp/send", json={"phone": phone})
    otp = send_res.json()["data"]["test_otp"]
    auth_res = await client.post("/api/v1/auth/otp/verify", json={"phone": phone, "otp": otp})
    access_token = auth_res.json()["data"]["access_token"]

    patch_res = await client.patch(
        "/api/v1/auth/profile",
        json={"full_name": "Rohan Deshmukh", "email": "rohan@example.com", "preferred_language": "hi"},
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert patch_res.status_code == 200
    data = patch_res.json()["data"]
    assert data["full_name"] == "Rohan Deshmukh"
    assert data["email"] == "rohan@example.com"
    assert data["preferred_language"] == "hi"


@pytest.mark.asyncio
async def test_dev_token_generator(client: AsyncClient):
    roles = ["SHOPPER", "MERCHANT", "SUPER_ADMIN"]
    for role in roles:
        res = await client.post("/api/v1/auth/dev-token", json={"role": role})
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["role"] == role
        assert data["access_token"] is not None
        assert data["refresh_token"] is not None
