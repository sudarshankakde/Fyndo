import hashlib
import json
import logging
from typing import Any, Dict, Optional
from app.core.config import settings
from app.core.redis import get_redis_client

logger = logging.getLogger("fyndo.session")


class SessionService:
    """
    Manages Redis-backed refresh token storage, rotation, and revocation
    as specified in docs/08_Authentication_Authorization.md Section 3.
    """

    @staticmethod
    def _token_hash(token: str) -> str:
        """Returns SHA-256 hash of the token string."""
        return hashlib.sha256(token.strip().encode("utf-8")).hexdigest()

    @classmethod
    async def store_refresh_session(
        cls,
        token: str,
        user_id: str,
        role: str,
        ttl_days: Optional[int] = None
    ) -> None:
        """Stores token hash in Redis mapped to user ID with expiration TTL."""
        try:
            redis = await get_redis_client()
            h = cls._token_hash(token)
            key = f"refresh:{h}"
            ttl = (ttl_days or settings.REFRESH_TOKEN_EXPIRE_DAYS) * 86400

            payload = json.dumps({"user_id": str(user_id), "role": role})
            await redis.set(key, payload, ex=ttl)
            logger.debug(f"Stored refresh session for user {user_id}")
        except Exception as e:
            logger.warning(f"Could not persist refresh session to Redis: {e}")

    @classmethod
    async def validate_refresh_session(cls, token: str) -> Optional[Dict[str, Any]]:
        """
        Validates token hash existence in Redis.
        Returns session dict if valid and unrevoked, None if revoked or missing.
        """
        try:
            redis = await get_redis_client()
            h = cls._token_hash(token)
            key = f"refresh:{h}"
            raw = await redis.get(key)
            if not raw:
                return None
            return json.loads(raw)
        except Exception as e:
            logger.warning(f"Redis session lookup failed: {e}")
            return None

    @classmethod
    async def revoke_refresh_session(cls, token: str) -> bool:
        """Invalidates a refresh token by deleting it from Redis."""
        try:
            redis = await get_redis_client()
            h = cls._token_hash(token)
            key = f"refresh:{h}"
            deleted = await redis.delete(key)
            return bool(deleted > 0)
        except Exception as e:
            logger.warning(f"Failed to revoke refresh session in Redis: {e}")
            return False

    @classmethod
    async def rotate_refresh_session(
        cls,
        old_token: str,
        new_token: str,
        user_id: str,
        role: str
    ) -> None:
        """Rotates refresh token: revokes old token and stores new one."""
        await cls.revoke_refresh_session(old_token)
        await cls.store_refresh_session(new_token, user_id, role)
