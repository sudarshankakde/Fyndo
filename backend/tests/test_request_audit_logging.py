"""Tests for production request logging, database impact tracing, and admin audit views."""
import asyncio
import uuid
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.database import Base, async_session_factory, engine
from app.main import app
from app.models.request_audit_log import RequestAuditLog

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture(autouse=True)
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _admin_token(client: AsyncClient) -> str:
    resp = await client.post("/api/v1/auth/dev-token", json={"role": "SUPER_ADMIN"})
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["access_token"]


async def test_request_and_db_queries_are_audited(client: AsyncClient):
    token = await _admin_token(client)

    # Issue an API call that touches the database
    resp = await client.get(
        "/api/v1/admin/stats",
        headers={"Authorization": f"Bearer {token}", "User-Agent": "TestClient/1.0"},
    )
    assert resp.status_code == 200
    req_id = resp.headers.get("x-request-id")
    assert req_id is not None

    # Wait briefly for non-blocking background audit task to complete
    await asyncio.sleep(0.3)

    # Query the audit log table
    async with async_session_factory() as session:
        log_entry = (
            await session.execute(
                select(RequestAuditLog).where(RequestAuditLog.request_id == req_id)
            )
        ).scalar_one_or_none()

        assert log_entry is not None
        assert log_entry.method == "GET"
        assert log_entry.path == "/api/v1/admin/stats"
        assert log_entry.status_code == 200
        assert log_entry.user_role == "SUPER_ADMIN"
        assert log_entry.user_agent == "TestClient/1.0"
        assert log_entry.duration_ms > 0
        # The admin stats endpoint executes DB queries (counts on merchants, reels, etc.)
        assert log_entry.db_query_count > 0
        assert log_entry.db_time_ms >= 0
        assert isinstance(log_entry.db_operations, dict)
        assert "SELECT" in log_entry.db_operations


async def test_sensitive_payload_fields_are_masked(client: AsyncClient):
    # Send a request with sensitive fields to admin-login
    resp = await client.post(
        "/api/v1/auth/admin-login",
        json={"identifier": "+919999900000", "password": "super_secret_password"},
        headers={"User-Agent": "AdminDesk/1.0"},
    )
    req_id = resp.headers.get("x-request-id")

    await asyncio.sleep(0.3)

    async with async_session_factory() as session:
        log_entry = (
            await session.execute(
                select(RequestAuditLog).where(RequestAuditLog.request_id == req_id)
            )
        ).scalar_one_or_none()

        assert log_entry is not None
        assert log_entry.request_body is not None
        assert "super_secret_password" not in log_entry.request_body
        assert "********" in log_entry.request_body


async def test_admin_audit_logs_rest_api(client: AsyncClient):
    token = await _admin_token(client)

    # Query the admin audit logs REST API
    resp = await client.get(
        "/api/v1/admin/audit-logs",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "logs" in data
    assert "total_count" in data
    assert "stats" in data
    assert isinstance(data["logs"], list)

    # Filter by user_role=SUPER_ADMIN
    resp_role = await client.get(
        "/api/v1/admin/audit-logs?user_role=SUPER_ADMIN",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_role.status_code == 200
    data_role = resp_role.json()["data"]
    for item in data_role["logs"]:
        assert "ADMIN" in (item["user_role"] or "")


async def test_admin_panel_html_audit_logs_view(client: AsyncClient):
    from app.admin.deps import issue_session

    session_cookie = issue_session("+919999900000")
    client.cookies.set("fyndo_admin_session", session_cookie)

    resp = await client.get("/admin/audit-logs?user_role=ALL")
    assert resp.status_code == 200
    assert "Request & Database Audit Console" in resp.text
    assert "User / Actor" in resp.text
    assert "Avg Latency" in resp.text
    assert "DB Queries Executed" in resp.text
