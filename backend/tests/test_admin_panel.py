"""Regression tests for the HTML super-admin panel.

Covers the dedicated login (cookie session), anonymous bounce, asset serving,
list/search, the htmx partial, and the full create → edit → delete cycle.
"""
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
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


async def _sign_in(client: AsyncClient) -> None:
    resp = await client.post(
        "/admin/login",
        data={
            "identifier": settings.SUPER_ADMIN_IDENTIFIER,
            "password": settings.SUPER_ADMIN_PASSWORD,
        },
    )
    assert resp.status_code == 303, resp.text
    assert "fyndo_admin_session" in client.cookies


def _phone() -> str:
    return f"+91{uuid.uuid4().int % 10_000_000_000:010d}"


async def test_anonymous_visitor_is_bounced_to_login(client: AsyncClient):
    resp = await client.get("/admin/")
    assert resp.status_code == 303
    assert resp.headers["location"] == "/admin/login"

    page = await client.get("/admin/login")
    assert page.status_code == 200
    assert "Sign in to" in page.text


async def test_login_rejects_bad_credentials(client: AsyncClient):
    resp = await client.post(
        "/admin/login",
        data={"identifier": settings.SUPER_ADMIN_IDENTIFIER, "password": "definitely-wrong"},
    )
    assert resp.status_code == 401
    assert "Invalid administrator credentials" in resp.text
    assert "fyndo_admin_session" not in client.cookies


async def test_static_assets_are_served(client: AsyncClient):
    css = await client.get("/admin/static/admin.css")
    assert css.status_code == 200
    assert "--blue" in css.text

    script = await client.get("/admin/static/htmx.min.js")
    assert script.status_code == 200
    assert len(script.content) > 10_000

    # Only files directly inside the panel's static directory are reachable.
    assert (await client.get("/admin/static/nope.css")).status_code == 404


async def test_dashboard_and_unknown_table(client: AsyncClient):
    await _sign_in(client)

    dash = await client.get("/admin/")
    assert dash.status_code == 200
    assert "Tables" in dash.text
    assert "Users" in dash.text

    missing = await client.get("/admin/not_a_table")
    assert missing.status_code == 404


async def test_htmx_list_request_returns_partial_only(client: AsyncClient):
    await _sign_in(client)

    partial = await client.get("/admin/users", headers={"HX-Request": "true"})
    assert partial.status_code == 200
    assert "<html" not in partial.text.lower()
    assert "card-head" in partial.text

    full = await client.get("/admin/users")
    assert "<html" in full.text.lower()
    # The ``&`` in generated URLs must be escaped exactly once.
    assert "&amp;amp;" not in full.text


async def test_full_crud_cycle_through_the_panel(client: AsyncClient):
    await _sign_in(client)
    phone = _phone()

    created = await client.post(
        "/admin/users/new",
        data={
            "full_name": "Panel Created",
            "phone": phone,
            "username": "",
            "profile_image_url": "",
            "email": "",
            "role": "SHOPPER",
            "preferred_language": "en",
            "is_active": "on",
        },
    )
    assert created.status_code == 303, created.text
    location = created.headers["location"]
    assert location.startswith("/admin/users/")
    pk = location.rsplit("/", 1)[-1].split("?")[0]

    detail = await client.get(f"/admin/users/{pk}")
    assert detail.status_code == 200
    assert phone in detail.text

    search = await client.get(f"/admin/users?q={phone}")
    assert search.status_code == 200
    assert "Panel Created" in search.text

    updated = await client.post(
        f"/admin/users/{pk}/edit",
        data={
            "full_name": "Panel Renamed",
            "phone": phone,
            "username": "",
            "profile_image_url": "",
            "email": "",
            "role": "MERCHANT",
            "preferred_language": "hi",
            "is_active": "",
        },
    )
    assert updated.status_code == 303, updated.text

    after = await client.get(f"/admin/users/{pk}")
    assert "Panel Renamed" in after.text
    assert "MERCHANT" in after.text
    assert "No" in after.text  # is_active was unchecked

    deleted = await client.post(f"/admin/users/{pk}/delete")
    assert deleted.status_code == 303
    assert (await client.get(f"/admin/users/{pk}")).status_code == 404


async def test_required_field_validation_is_reported(client: AsyncClient):
    await _sign_in(client)

    resp = await client.post("/admin/users/new", data={"full_name": "No Phone"})
    assert resp.status_code == 422
    assert "required" in resp.text.lower()


async def test_delete_with_htmx_uses_hx_redirect(client: AsyncClient):
    await _sign_in(client)
    phone = _phone()

    created = await client.post(
        "/admin/users/new",
        data={"full_name": "Doomed", "phone": phone, "role": "SHOPPER", "preferred_language": "en"},
    )
    pk = created.headers["location"].rsplit("/", 1)[-1].split("?")[0]

    resp = await client.post(f"/admin/users/{pk}/delete", headers={"HX-Request": "true"})
    assert resp.status_code == 200
    assert resp.headers["HX-Redirect"] == "/admin/users?ok=Row+deleted"


async def test_logout_clears_the_session(client: AsyncClient):
    await _sign_in(client)
    assert (await client.get("/admin/")).status_code == 200

    out = await client.get("/admin/logout")
    assert out.status_code == 303
    assert out.headers["location"] == "/admin/login"
    assert (await client.get("/admin/")).status_code == 303
