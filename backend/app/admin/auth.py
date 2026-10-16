"""Dedicated super-admin login for the HTML panel."""
import logging

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from app.admin.deps import (
    LOGIN_PATH,
    clear_session_cookie,
    current_admin,
    issue_session,
    read_session,
    set_session_cookie,
)
from app.admin.templating import templates
from app.core.config import settings
from app.core.database import async_session_factory
from app.core.security import verify_password
from app.models import User

logger = logging.getLogger("fyndo.admin")
router = APIRouter()

DEFAULT_LANDING = "/admin"


def _safe_next(candidate: str) -> str:
    """Only ever redirect within the panel (prevents open-redirect abuse)."""
    if candidate and candidate.startswith("/admin"):
        return candidate
    return DEFAULT_LANDING


async def _verify_admin(identifier: str, password: str) -> bool:
    """Master credentials first, then a DB user holding the SUPER_ADMIN role."""
    master_ok = (
        identifier == settings.SUPER_ADMIN_IDENTIFIER
        or identifier.lower() == (settings.SUPER_ADMIN_EMAIL or "").lower()
    ) and password == settings.SUPER_ADMIN_PASSWORD
    if master_ok:
        return True

    async with async_session_factory() as db:
        stmt = select(User).where((User.phone == identifier) | (User.email == identifier))
        user = (await db.execute(stmt)).scalars().first()
        if not user or not user.password_hash:
            return False
        role = str(getattr(user.role, "value", user.role)).upper()
        return role == "SUPER_ADMIN" and verify_password(password, user.password_hash)


@router.get("/login")
async def login_form(request: Request, next: str = DEFAULT_LANDING):
    if read_session(request):
        return RedirectResponse(DEFAULT_LANDING, status_code=303)
    return templates.TemplateResponse(
        request, "login.html", {"error": None, "next": _safe_next(next)}
    )


@router.post("/login")
async def login_submit(request: Request):
    form = await request.form()
    identifier = str(form.get("identifier", "")).strip()
    password = str(form.get("password", ""))
    next_url = _safe_next(str(form.get("next", DEFAULT_LANDING)))

    if not identifier or not password:
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": "Enter your administrator ID and password.", "next": next_url},
            status_code=400,
        )

    if not await _verify_admin(identifier, password):
        logger.warning("Rejected admin panel login for identifier=%s", identifier)
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": "Invalid administrator credentials.", "next": next_url},
            status_code=401,
        )

    logger.info("Admin panel login succeeded for identifier=%s", identifier)
    response = RedirectResponse(next_url, status_code=303)
    set_session_cookie(response, issue_session(identifier))
    return response


@router.get("/logout")
@router.post("/logout")
async def logout(request: Request, admin=current_admin):
    response = RedirectResponse(LOGIN_PATH, status_code=303)
    clear_session_cookie(response)
    return response
