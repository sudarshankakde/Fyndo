"""Redis-backed fixed-window rate limiting.

Used for feed polling (60 req/min) and POS redemption (30 req/min) as
specified in docs/05_System_Architecture.md section 4.
"""
import hashlib
import logging
from typing import Callable, Optional

from fastapi import HTTPException, Request, status

from app.core.config import settings
from app.core.redis import get_redis_client

logger = logging.getLogger("fyndo.rate_limit")


def _identity(request: Request) -> str:
    auth = request.headers.get("authorization")
    if auth:
        return auth
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "anonymous"


def rate_limit(
    bucket: str,
    limit: int,
    window_seconds: int = 60,
) -> Callable:
    """Builds a FastAPI dependency enforcing `limit` requests per window."""

    async def dependency(request: Request) -> None:
        if not settings.ENABLE_RATE_LIMITING or limit <= 0:
            return

        identity = _identity(request)
        digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:32]
        key = f"rate:{bucket}:{digest}"

        try:
            redis = await get_redis_client()
            attempts = await redis.incr(key)
            if attempts == 1:
                await redis.expire(key, window_seconds)
            if attempts > limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests. Please slow down and try again shortly.",
                )
        except HTTPException:
            raise
        except Exception as exc:  # fail-open: limiting must never take the API down
            logger.warning(f"Rate limiter unavailable for bucket '{bucket}': {exc}")

    return dependency


def optional_rate_limit(bucket: str, limit: int, window_seconds: int = 60) -> Optional[Callable]:
    return rate_limit(bucket, limit, window_seconds) if settings.ENABLE_RATE_LIMITING else None
