"""Request-scoped context propagated into every log record.

Values are stored in ``contextvars`` so they stay isolated per asyncio task
(and therefore per HTTP request) without threading state through call sites.
"""
import contextvars
import uuid
from typing import Optional

request_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "request_id", default=None
)
user_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "user_id", default=None
)
client_ip_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "client_ip", default=None
)


def new_request_id() -> str:
    """Returns a short, unique, URL/header safe correlation id."""
    return uuid.uuid4().hex


def set_request_context(*, request_id: str, client_ip: Optional[str] = None) -> None:
    request_id_var.set(request_id)
    client_ip_var.set(client_ip)


def set_user_id(user_id: Optional[object]) -> None:
    """Binds the authenticated principal to the current request context."""
    user_id_var.set(str(user_id) if user_id else None)


def clear_request_context() -> None:
    request_id_var.set(None)
    user_id_var.set(None)
    client_ip_var.set(None)


def get_request_id() -> Optional[str]:
    return request_id_var.get()
