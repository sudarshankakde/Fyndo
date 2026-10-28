"""ASGI middleware that correlates, logs, and audits inbound HTTP requests and DB effects.

Implements raw ASGI middleware to ensure zero buffering overhead for video streams,
captures client metadata (IP, User-Agent, User ID, Role), tracks all database
queries executed during the request lifecycle, and persists full audit traces.
"""
import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.context import clear_request_context, new_request_id, set_request_context
from app.core.db_query_tracker import (
    start_tracking_db_queries,
    stop_tracking_db_queries,
    summarize_db_impact,
)
from app.services.audit_service import persist_request_audit_log

access_logger = logging.getLogger("fyndo.access")

_MAX_REQUEST_ID_LENGTH = 64
_MAX_BODY_CAPTURE_BYTES = 16384  # 16 KB max capture for audit inspection

_IGNORED_AUDIT_PREFIXES = (
    "/admin/static/",
    "/static/",
    "/favicon.ico",
    "/api/v1/health",
)

_SENSITIVE_FIELD_NAMES = {
    "password",
    "pin",
    "otp",
    "token",
    "secret",
    "access_token",
    "refresh_token",
    "authorization",
    "backup_pin",
    "current_password",
    "new_password",
}


def _mask_sensitive_data(data: Any) -> Any:
    """Recursively masks passwords, secrets, OTPs, and authentication tokens."""
    if isinstance(data, dict):
        masked = {}
        for key, val in data.items():
            if str(key).lower() in _SENSITIVE_FIELD_NAMES:
                masked[key] = "********"
            else:
                masked[key] = _mask_sensitive_data(val)
        return masked
    elif isinstance(data, list):
        return [_mask_sensitive_data(item) for item in data]
    return data


def _sanitize_payload(body_bytes: bytes, content_type: str) -> Optional[str]:
    """Sanitizes request body for safe audit storage."""
    if not body_bytes:
        return None

    if "application/json" in content_type:
        try:
            parsed = json.loads(body_bytes.decode("utf-8", errors="replace"))
            sanitized = _mask_sensitive_data(parsed)
            res = json.dumps(sanitized)
            return res[:4000]
        except Exception:
            pass

    if "application/x-www-form-urlencoded" in content_type:
        return "[Form Encoded Data]"

    if "multipart/form-data" in content_type:
        return f"[Multipart Upload: {len(body_bytes)} bytes]"

    decoded = body_bytes.decode("utf-8", errors="replace")
    return decoded[:2000]


def _extract_user_context(headers: Dict[str, str]) -> Tuple[Optional[str], Optional[str]]:
    """Decodes JWT payload or admin session without signature verification to extract user identifier and role."""
    auth = headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        token = auth[7:].strip()
        try:
            import jwt

            payload = jwt.decode(token, options={"verify_signature": False})
            return payload.get("sub"), payload.get("role")
        except Exception:
            pass

    cookie_str = headers.get("cookie", "")
    if cookie_str:
        for item in cookie_str.split(";"):
            parts = item.strip().split("=", 1)
            if len(parts) == 2:
                name, val = parts[0].strip(), parts[1].strip()
                if name == "fyndo_admin_session" and val:
                    try:
                        import jwt

                        payload = jwt.decode(val, options={"verify_signature": False})
                        return payload.get("sub"), payload.get("role") or "SUPER_ADMIN"
                    except Exception:
                        return val[:36], "SUPER_ADMIN"
                elif name in ("access_token", "token") and val:
                    try:
                        import jwt

                        payload = jwt.decode(val, options={"verify_signature": False})
                        return payload.get("sub"), payload.get("role")
                    except Exception:
                        pass
    return None, None


class RequestLoggingMiddleware:
    """Correlates, logs, and audits every inbound HTTP request and its database impact."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

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

        user_agent = headers.get("user-agent")
        user_id, user_role = _extract_user_context(headers)
        content_type = headers.get("content-type", "")

        set_request_context(request_id=request_id, client_ip=client_ip)

        # Buffer incoming payload chunks passively as downstream reads them
        captured_body_chunks: List[bytes] = []
        captured_bytes_total = 0

        async def receive_wrapper() -> Message:
            nonlocal captured_bytes_total
            message = await receive()
            if message["type"] == "http.request":
                chunk = message.get("body", b"")
                if chunk and captured_bytes_total < _MAX_BODY_CAPTURE_BYTES:
                    to_take = min(len(chunk), _MAX_BODY_CAPTURE_BYTES - captured_bytes_total)
                    captured_body_chunks.append(chunk[:to_take])
                    captured_bytes_total += to_take
            return message

        status_code = 500
        response_bytes_total = 0
        started = time.perf_counter()

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code, response_bytes_total
            if message["type"] == "http.response.start":
                status_code = message.get("status", 500)
                resp_headers = list(message.get("headers") or [])
                resp_headers.append((b"x-request-id", request_id.encode("latin-1")))
                message = {**message, "headers": resp_headers}
            elif message["type"] == "http.response.body":
                body_chunk = message.get("body", b"")
                if body_chunk:
                    response_bytes_total += len(body_chunk)
            await send(message)

        # Begin tracking SQL queries executed during this request
        start_tracking_db_queries()
        error_detail: Optional[str] = None

        try:
            await self.app(scope, receive_wrapper, send_wrapper)
        except Exception as exc:
            error_detail = str(exc)
            access_logger.exception("Unhandled exception during request [%s]: %s", request_id, exc)
            raise
        finally:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            db_queries = stop_tracking_db_queries()
            db_summary = summarize_db_impact(db_queries)

            # Structured stdout logging
            self._log_access(
                scope,
                status_code,
                duration_ms,
                client_ip,
                user_id,
                db_summary,
            )

            # Background persistence for admin inspection (excluding health and static assets)
            path = scope.get("path", "-")
            if not any(path.startswith(prefix) for prefix in _IGNORED_AUDIT_PREFIXES):
                query_string = scope.get("query_string", b"").decode("latin-1")
                raw_body = b"".join(captured_body_chunks)
                sanitized_body = _sanitize_payload(raw_body, content_type)

                asyncio.create_task(
                    persist_request_audit_log(
                        request_id=request_id,
                        method=scope.get("method", "GET"),
                        path=path,
                        query_params=query_string if query_string else None,
                        status_code=status_code,
                        duration_ms=duration_ms,
                        client_ip=client_ip,
                        user_agent=user_agent,
                        user_id=user_id,
                        user_role=user_role,
                        request_body=sanitized_body,
                        response_size=response_bytes_total if response_bytes_total > 0 else None,
                        error_message=error_detail,
                        db_summary=db_summary,
                    )
                )

            clear_request_context()

    @staticmethod
    def _log_access(
        scope: Scope,
        status_code: int,
        duration_ms: float,
        client_ip: Optional[str],
        user_id: Optional[str],
        db_summary: Dict[str, Any],
    ) -> None:
        method = scope.get("method", "-")
        path = scope.get("path", "-")
        level = logging.INFO if status_code < 500 else logging.ERROR

        db_time = db_summary.get("db_time_ms", 0.0)
        query_count = db_summary.get("query_count", 0)

        access_logger.log(
            level,
            "%s %s -> %s in %sms (DB: %sms, %s queries)",
            method,
            path,
            status_code,
            duration_ms,
            db_time,
            query_count,
            extra={
                "event": "http_request",
                "http_method": method,
                "path": path,
                "status_code": status_code,
                "duration_ms": duration_ms,
                "client_ip": client_ip,
                "user_id": user_id,
                "db_queries": query_count,
                "db_time_ms": db_time,
                "tables_affected": db_summary.get("tables_affected", []),
            },
        )
