"""Panel session handling.

The panel keeps its own signed session cookie (``fyndo_admin_session``) instead
of reusing the API's bearer-token dependency, so a leaked shopper/merchant JWT
can never be replayed against the back office, and the panel's own viewers can
be reviewed independently of the mobile API.
"""
import logging
from datetime import timedelta
from typing import Any, Dict, Optional

from fastapi import Request
from fastapi.responses import RedirectResponse

from app.core.config import settings
from app.core.security import create_access_token, decode_access_token

logger = logging.getLogger("fyndo.admin")

COOKIE_NAME = "fyndo_admin_session"
SESSION_SCOPE = "admin_panel"
SESSION_TTL_MINUTES = 8 * 60
LOGIN_PATH = "/admin/login"


class RedirectToLogin(Exception):
    """Raised by panel dependencies to bounce an anonymous visitor to login."""


async def redirect_to_login_handler(request: Request, exc: RedirectToLogin) -> RedirectResponse:
    """Registered on the app so panel redirects survive the global 4xx handler."""
    return RedirectResponse(LOGIN_PATH, status_code=303)


def issue_session(identifier: str) -> str:
    """Mints the panel session cookie value."""
    return create_access_token(
        subject=identifier,
        role="SUPER_ADMIN",
        extra_claims={"scope": SESSION_SCOPE},
        expires_delta=timedelta(minutes=SESSION_TTL_MINUTES),
    )


def read_session(request: Request) -> Optional[Dict[str, Any]]:
    """Returns the decoded panel session, or ``None`` when absent/invalid."""
    raw = request.cookies.get(COOKIE_NAME)
    if not raw:
        return None
    payload = decode_access_token(raw)
    if not payload:
        return None
    if payload.get("scope") != SESSION_SCOPE:
        return None
    if str(payload.get("role", "")).upper() != "SUPER_ADMIN":
        return None
    return payload


def current_admin(request: Request) -> Dict[str, Any]:
    """Dependency guarding every panel route."""
    payload = read_session(request)
    if not payload:
        raise RedirectToLogin()
    return payload


def set_session_cookie(response, token: str) -> None:
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=SESSION_TTL_MINUTES * 60,
        httponly=True,
        samesite="lax",
        secure=settings.is_production,
        path="/admin",
    )


def clear_session_cookie(response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/admin")
