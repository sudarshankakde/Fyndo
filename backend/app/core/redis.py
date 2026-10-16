import logging
from typing import Optional
import redis.asyncio as aioredis
from app.core.config import settings

logger = logging.getLogger("fyndo.redis")

_redis_client: Optional[aioredis.Redis] = None


async def get_redis_client() -> aioredis.Redis:
    """
    Returns an active async Redis client.

    Outside development an unreachable Redis is a hard failure, because OTP
    secrets, refresh sessions, rate limits and redemption locks all depend on
    it. In development we fall back to fakeredis for convenience.
    """
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    try:
        client = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_timeout=2.0,
            socket_connect_timeout=2.0,
        )
        await client.ping()
        _redis_client = client
        logger.info("Connected successfully to standalone Redis instance.")
        return _redis_client
    except Exception as e:
        if settings.REDIS_REQUIRED:
            logger.error(f"Redis is required but unreachable at {settings.REDIS_URL}: {e}")
            raise RuntimeError(
                f"Redis is required but unreachable at {settings.REDIS_URL}: {e}"
            ) from e

        logger.warning(
            f"Unable to connect to Redis at {settings.REDIS_URL}: {e}. "
            "Falling back to in-memory FakeRedis for local development."
        )
        try:
            import fakeredis.aioredis
            _redis_client = fakeredis.aioredis.FakeRedis(decode_responses=True)
            return _redis_client
        except ImportError:
            raise RuntimeError("Redis connection failed and fakeredis is not installed.")


async def close_redis_client() -> None:
    global _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None
