import logging
from typing import Optional
import redis.asyncio as aioredis
from app.core.config import settings

logger = logging.getLogger("fyndo.redis")

_redis_client: Optional[aioredis.Redis] = None


async def get_redis_client() -> aioredis.Redis:
    """
    Returns an active async Redis client.
    Gracefully falls back to fakeredis if the standalone server is unreachable.
    """
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    try:
        client = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_timeout=2.0,
            socket_connect_timeout=2.0
        )
        await client.ping()
        _redis_client = client
        logger.info("Connected successfully to standalone Redis instance.")
        return _redis_client
    except Exception as e:
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
