"""ASGI middleware that emits one structured log line per HTTP request.

Implemented as a raw ASGI middleware (not ``BaseHTTPMiddleware``) so that it
never buffers streaming responses such as reel video or media uploads. It
assigns a correlation id, propagates it via the ``X-Request-ID`` response
header, and logs method, path, status and latency for every request.
"""
import logging
import time
from typing import Optional, Tuple

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.context import clear_request_context, new_request_id, set_request_context

access_logger = logging.getLogger("fyndo.access")

_MAX_REQUEST_ID_LENGTH = 64


class RequestLoggingMiddleware:
    """Correlates and logs every inbound HTTP request."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id, client_ip = self._extract_context(scope)
        set_request_context(request_id=request_id, client_ip=client_ip)

        status_code = 500
        started = time.perf_counter()

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 500)
                headers = list(message.get("headers") or [])
                headers.append((b"x-request-id", request_id.encode("latin-1")))
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            self._log(scope, status_code, duration_ms)
            clear_request_context()

    @staticmethod
    def _extract_context(scope: Scope) -> Tuple[str, Optional[str]]:
        headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in (scope.get("headers") or [])
        }
        request_id = (headers.get("x-request-id") or "").strip()[:_MAX_REQUEST_ID_LENGTH]
        if not request_id:
            request_id = new_request_id()

        client = scope.get("client")
        client_ip = client[0] if client else None
        forwarded = headers.get("x-forwarded-for")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip() or client_ip
        return request_id, client_ip

    @staticmethod
    def _log(scope: Scope, status_code: int, duration_ms: float) -> None:
        method = scope.get("method", "-")
        path = scope.get("path", "-")
        level = logging.INFO if status_code < 500 else logging.ERROR
        access_logger.log(
            level,
            "%s %s -> %s in %sms",
            method,
            path,
            status_code,
            duration_ms,
            extra={
                "event": "http_request",
                "http_method": method,
                "path": path,
                "status_code": status_code,
                "duration_ms": duration_ms,
            },
        )
